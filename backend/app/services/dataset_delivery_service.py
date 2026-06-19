"""Dataset delivery service - handles CSV export from real database queries."""
import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import uuid
import json
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetPurchase, DatasetType
from app.services.cloud_storage_service import get_cloud_storage

logger = logging.getLogger(__name__)


class DatasetDeliveryService:
    TEMP_STORAGE_PATH = "/tmp/dataset_exports"

    def __init__(self):
        os.makedirs(self.TEMP_STORAGE_PATH, exist_ok=True)

    def _get_query_filters(self, dataset: Dataset) -> Dict[str, Any]:
        qd = dataset.query_definition or {}
        return {
            "vertical": qd.get("vertical") or dataset.vertical,
            "city": qd.get("city") or dataset.city,
            "state": qd.get("state"),
            "min_score": qd.get("min_score", 0.0),
            "max_results": qd.get("max_results", dataset.record_count or 100),
            "category": qd.get("category"),
        }

    def generate_csv_file(self, dataset: Dataset, db: Session) -> Tuple[str, int]:
        file_path = os.path.join(self.TEMP_STORAGE_PATH, f"{dataset.id}_{datetime.utcnow().isoformat()}.csv")
        dt = dataset.dataset_type
        dt_val = dt.value if hasattr(dt, 'value') else dt
        if dt_val == DatasetType.OPPORTUNITIES.value or dt == DatasetType.OPPORTUNITIES:
            result_path, row_count = self._export_opportunities(dataset, file_path, db)
        elif dt_val == DatasetType.MARKETS.value or dt == DatasetType.MARKETS:
            result_path, row_count = self._export_markets(dataset, file_path, db)
        elif dt_val == DatasetType.TRENDS.value or dt == DatasetType.TRENDS:
            result_path, row_count = self._export_trends(dataset, file_path, db)
        elif dt_val == DatasetType.RAW_DATA.value or dt == DatasetType.RAW_DATA:
            result_path, row_count = self._export_raw_data(dataset, file_path, db)
        else:
            raise ValueError(f"Unknown dataset type: {dataset.dataset_type}")
        storage = get_cloud_storage()
        if storage.is_configured() and storage.provider != "local":
            object_key = f"datasets/{dataset.id}/{os.path.basename(result_path)}"
            success, error = storage.upload_file(result_path, object_key, "text/csv")
            if success:
                logger.info(f"[DatasetDelivery] Uploaded dataset {dataset.id} to cloud storage: {object_key}")
                return object_key, row_count
            else:
                logger.warning(f"[DatasetDelivery] Cloud upload failed, keeping local file: {error}")
        return result_path, row_count

    # -------------------------------------------------------------------------
    # Query helpers (shared between export and preview)
    # -------------------------------------------------------------------------

    def _query_opportunities(self, dataset: Dataset, db: Session) -> List[Any]:
        filters = self._get_query_filters(dataset)
        max_results = filters.get("max_results", 100)
        try:
            from app.models.data_hub import HubOpportunityEnriched
            query = db.query(HubOpportunityEnriched)
            if filters.get("city"):
                query = query.filter(HubOpportunityEnriched.city.ilike(f"%{filters['city']}%"))
            if filters.get("state"):
                query = query.filter(HubOpportunityEnriched.state.ilike(f"%{filters['state']}%"))
            if filters.get("vertical"):
                query = query.filter(HubOpportunityEnriched.category.ilike(f"%{filters['vertical']}%"))
            if filters.get("min_score"):
                query = query.filter(HubOpportunityEnriched.ai_opportunity_score >= filters["min_score"])
            query = query.order_by(HubOpportunityEnriched.ai_opportunity_score.desc()).limit(max_results)
            return query.all()
        except Exception as e:
            logger.warning(f"[DatasetDelivery] Could not query HubOpportunityEnriched: {e}")
            return []

    def _query_markets(self, dataset: Dataset, db: Session) -> List[Any]:
        filters = self._get_query_filters(dataset)
        max_results = filters.get("max_results", 100)
        try:
            from app.models.data_hub import HubMarketByGeography
            query = db.query(HubMarketByGeography)
            if filters.get("city"):
                query = query.filter(HubMarketByGeography.city.ilike(f"%{filters['city']}%"))
            if filters.get("state"):
                query = query.filter(HubMarketByGeography.state.ilike(f"%{filters['state']}%"))
            query = query.limit(max_results)
            return query.all()
        except Exception as e:
            logger.warning(f"[DatasetDelivery] Could not query HubMarketByGeography: {e}")
            return []

    def _query_trends(self, dataset: Dataset, db: Session) -> List[Any]:
        filters = self._get_query_filters(dataset)
        max_results = filters.get("max_results", 100)
        try:
            from app.models.detected_trend import DetectedTrend
            query = db.query(DetectedTrend)
            if filters.get("vertical"):
                query = query.filter(DetectedTrend.category.ilike(f"%{filters['vertical']}%"))
            query = query.order_by(DetectedTrend.trend_strength.desc()).limit(max_results)
            return query.all()
        except Exception as e:
            logger.warning(f"[DatasetDelivery] Could not query DetectedTrend: {e}")
            return []

    def _query_raw_data(self, dataset: Dataset, db: Session) -> List[Any]:
        filters = self._get_query_filters(dataset)
        max_results = filters.get("max_results", 100)
        try:
            from app.models.data_source import ScrapeJob
            query = db.query(ScrapeJob).order_by(ScrapeJob.completed_at.desc()).limit(max_results)
            return query.all()
        except Exception as e:
            logger.warning(f"[DatasetDelivery] Could not query ScrapeJob: {e}")
            return []

    # -------------------------------------------------------------------------
    # Preview methods (return dicts for the preview endpoint)
    # -------------------------------------------------------------------------

    def preview_opportunities(self, dataset: Dataset, db: Session) -> Tuple[List[str], List[Dict]]:
        rows = self._query_opportunities(dataset, db)
        if not rows:
            return [], []
        columns = [
            'opportunity_id', 'title', 'category', 'city', 'state',
            'ai_opportunity_score', 'market_tier', 'trend_momentum', 'competition_density',
            'estimated_market_size_usd', 'estimated_startup_cost_usd', 'estimated_monthly_revenue_usd',
            'roi_estimate_percent', 'break_even_months', 'confidence_score', 'data_freshness', 'data_source',
        ]
        result = []
        for row in rows:
            result.append({
                'opportunity_id': getattr(row, 'opportunity_id', row.id),
                'title': getattr(row, 'title', ''),
                'category': getattr(row, 'category', ''),
                'city': getattr(row, 'city', ''),
                'state': getattr(row, 'state', ''),
                'ai_opportunity_score': getattr(row, 'ai_opportunity_score', ''),
                'market_tier': getattr(row, 'market_tier', ''),
                'trend_momentum': getattr(row, 'trend_momentum', ''),
                'competition_density': getattr(row, 'competition_density', ''),
                'estimated_market_size_usd': getattr(row, 'estimated_market_size_usd', ''),
                'estimated_startup_cost_usd': getattr(row, 'estimated_startup_cost_usd', ''),
                'estimated_monthly_revenue_usd': getattr(row, 'estimated_monthly_revenue_usd', ''),
                'roi_estimate_percent': getattr(row, 'roi_estimate_percent', ''),
                'break_even_months': getattr(row, 'break_even_months', ''),
                'confidence_score': getattr(row, 'confidence_score', ''),
                'data_freshness': getattr(row, 'data_freshness', 'unknown') or 'unknown',
                'data_source': 'HubOpportunityEnriched (real)',
            })
        return columns, result

    def preview_markets(self, dataset: Dataset, db: Session) -> Tuple[List[str], List[Dict]]:
        rows = self._query_markets(dataset, db)
        if not rows:
            return [], []
        columns = ['market_id', 'city', 'state', 'country', 'total_opportunities', 'categories', 'avg_score', 'market_health', 'data_source']
        result = []
        for row in rows:
            categories = getattr(row, 'categories', None)
            result.append({
                'market_id': getattr(row, 'market_id', row.id),
                'city': getattr(row, 'city', ''),
                'state': getattr(row, 'state', ''),
                'country': getattr(row, 'country', 'USA'),
                'total_opportunities': getattr(row, 'total_opportunities', ''),
                'categories': json.dumps(categories) if categories else '[]',
                'avg_score': 0,
                'market_health': 'unknown',
                'data_source': 'HubMarketByGeography (real)',
            })
        return columns, result

    def preview_trends(self, dataset: Dataset, db: Session) -> Tuple[List[str], List[Dict]]:
        rows = self._query_trends(dataset, db)
        if not rows:
            return [], []
        columns = [
            'id', 'trend_name', 'trend_strength', 'category', 'source_type',
            'opportunities_count', 'growth_rate', 'confidence_score', 'keywords', 'detected_at', 'data_source',
        ]
        result = []
        for row in rows:
            keywords = getattr(row, 'keywords', None)
            detected_at = getattr(row, 'detected_at', None)
            result.append({
                'id': row.id,
                'trend_name': getattr(row, 'trend_name', ''),
                'trend_strength': getattr(row, 'trend_strength', ''),
                'category': getattr(row, 'category', ''),
                'source_type': getattr(row, 'source_type', ''),
                'opportunities_count': getattr(row, 'opportunities_count', ''),
                'growth_rate': getattr(row, 'growth_rate', ''),
                'confidence_score': getattr(row, 'confidence_score', ''),
                'keywords': json.dumps(keywords) if keywords else '[]',
                'detected_at': detected_at.isoformat() if detected_at else '',
                'data_source': 'DetectedTrend (real)',
            })
        return columns, result

    def preview_raw_data(self, dataset: Dataset, db: Session) -> Tuple[List[str], List[Dict]]:
        rows = self._query_raw_data(dataset, db)
        if not rows:
            return [], []
        columns = [
            'job_id', 'source_name', 'job_type', 'status',
            'items_processed', 'items_accepted', 'items_rejected',
            'error_message', 'completed_at', 'created_at', 'data_source',
        ]
        result = []
        for row in rows:
            completed_at = getattr(row, 'completed_at', None)
            created_at = getattr(row, 'created_at', None)
            result.append({
                'job_id': row.id,
                'source_name': getattr(row, 'source_name', ''),
                'job_type': getattr(row, 'job_type', ''),
                'status': getattr(row, 'status', ''),
                'items_processed': getattr(row, 'items_processed', ''),
                'items_accepted': getattr(row, 'items_accepted', ''),
                'items_rejected': getattr(row, 'items_rejected', ''),
                'error_message': getattr(row, 'error_message', '') or '',
                'completed_at': completed_at.isoformat() if completed_at else '',
                'created_at': created_at.isoformat() if created_at else '',
                'data_source': 'ScrapeJob (real)',
            })
        return columns, result

    # -------------------------------------------------------------------------
    # CSV Export methods (query real data, NO mock fallback)
    # -------------------------------------------------------------------------

    def generate_csv_file(self, dataset: Dataset, db: Session) -> Tuple[str, int]:
        file_path = os.path.join(self.TEMP_STORAGE_PATH, f"{dataset.id}_{datetime.utcnow().isoformat()}.csv")
        dt = dataset.dataset_type
        dt_val = dt.value if hasattr(dt, 'value') else dt
        if dt_val == DatasetType.OPPORTUNITIES.value or dt == DatasetType.OPPORTUNITIES:
            result_path, row_count = self._export_opportunities(dataset, file_path, db)
        elif dt_val == DatasetType.MARKETS.value or dt == DatasetType.MARKETS:
            result_path, row_count = self._export_markets(dataset, file_path, db)
        elif dt_val == DatasetType.TRENDS.value or dt == DatasetType.TRENDS:
            result_path, row_count = self._export_trends(dataset, file_path, db)
        elif dt_val == DatasetType.RAW_DATA.value or dt == DatasetType.RAW_DATA:
            result_path, row_count = self._export_raw_data(dataset, file_path, db)
        else:
            raise ValueError(f"Unknown dataset type: {dataset.dataset_type}")
        storage = get_cloud_storage()
        if storage.is_configured() and storage.provider != "local":
            object_key = f"datasets/{dataset.id}/{os.path.basename(result_path)}"
            success, error = storage.upload_file(result_path, object_key, "text/csv")
            if success:
                logger.info(f"[DatasetDelivery] Uploaded dataset {dataset.id} to cloud storage: {object_key}")
                return object_key, row_count
            else:
                logger.warning(f"[DatasetDelivery] Cloud upload failed, keeping local file: {error}")
        return result_path, row_count

    def _export_opportunities(self, dataset: Dataset, file_path: str, db: Session) -> Tuple[str, int]:
        rows = self._query_opportunities(dataset, db)
        if not rows:
            logger.warning(f"No real opportunity data for dataset {dataset.id}")
            return file_path, 0
        fieldnames = [
            'opportunity_id', 'title', 'category', 'city', 'state',
            'ai_opportunity_score', 'market_tier', 'trend_momentum', 'competition_density',
            'estimated_market_size_usd', 'estimated_startup_cost_usd', 'estimated_monthly_revenue_usd',
            'roi_estimate_percent', 'break_even_months', 'confidence_score', 'data_freshness', 'data_source',
        ]
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    'opportunity_id': getattr(row, 'opportunity_id', row.id),
                    'title': getattr(row, 'title', ''),
                    'category': getattr(row, 'category', ''),
                    'city': getattr(row, 'city', ''),
                    'state': getattr(row, 'state', ''),
                    'ai_opportunity_score': getattr(row, 'ai_opportunity_score', ''),
                    'market_tier': getattr(row, 'market_tier', ''),
                    'trend_momentum': getattr(row, 'trend_momentum', ''),
                    'competition_density': getattr(row, 'competition_density', ''),
                    'estimated_market_size_usd': getattr(row, 'estimated_market_size_usd', ''),
                    'estimated_startup_cost_usd': getattr(row, 'estimated_startup_cost_usd', ''),
                    'estimated_monthly_revenue_usd': getattr(row, 'estimated_monthly_revenue_usd', ''),
                    'roi_estimate_percent': getattr(row, 'roi_estimate_percent', ''),
                    'break_even_months': getattr(row, 'break_even_months', ''),
                    'confidence_score': getattr(row, 'confidence_score', ''),
                    'data_freshness': getattr(row, 'data_freshness', 'unknown') or 'unknown',
                    'data_source': 'HubOpportunityEnriched (real)',
                })
        logger.info(f"Exported {len(rows)} real opportunities to {file_path}")
        return file_path, len(rows)

    def _export_markets(self, dataset: Dataset, file_path: str, db: Session) -> Tuple[str, int]:
        rows = self._query_markets(dataset, db)
        if not rows:
            logger.warning(f"No real market data for dataset {dataset.id}")
            return file_path, 0
        fieldnames = ['market_id', 'city', 'state', 'country', 'total_opportunities', 'categories', 'avg_score', 'market_health', 'data_source']
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                categories = getattr(row, 'categories', None)
                writer.writerow({
                    'market_id': getattr(row, 'market_id', row.id),
                    'city': getattr(row, 'city', ''),
                    'state': getattr(row, 'state', ''),
                    'country': getattr(row, 'country', 'USA'),
                    'total_opportunities': getattr(row, 'total_opportunities', ''),
                    'categories': json.dumps(categories) if categories else '[]',
                    'avg_score': 0,
                    'market_health': 'unknown',
                    'data_source': 'HubMarketByGeography (real)',
                })
        logger.info(f"Exported {len(rows)} real markets to {file_path}")
        return file_path, len(rows)

    def _export_trends(self, dataset: Dataset, file_path: str, db: Session) -> Tuple[str, int]:
        rows = self._query_trends(dataset, db)
        if not rows:
            logger.warning(f"No real trend data for dataset {dataset.id}")
            return file_path, 0
        fieldnames = [
            'id', 'trend_name', 'trend_strength', 'category', 'source_type',
            'opportunities_count', 'growth_rate', 'confidence_score', 'keywords', 'detected_at', 'data_source',
        ]
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                keywords = getattr(row, 'keywords', None)
                detected_at = getattr(row, 'detected_at', None)
                writer.writerow({
                    'id': row.id,
                    'trend_name': getattr(row, 'trend_name', ''),
                    'trend_strength': getattr(row, 'trend_strength', ''),
                    'category': getattr(row, 'category', ''),
                    'source_type': getattr(row, 'source_type', ''),
                    'opportunities_count': getattr(row, 'opportunities_count', ''),
                    'growth_rate': getattr(row, 'growth_rate', ''),
                    'confidence_score': getattr(row, 'confidence_score', ''),
                    'keywords': json.dumps(keywords) if keywords else '[]',
                    'detected_at': detected_at.isoformat() if detected_at else '',
                    'data_source': 'DetectedTrend (real)',
                })
        logger.info(f"Exported {len(rows)} real trends to {file_path}")
        return file_path, len(rows)

    def _export_raw_data(self, dataset: Dataset, file_path: str, db: Session) -> Tuple[str, int]:
        rows = self._query_raw_data(dataset, db)
        if not rows:
            logger.warning(f"No real scrape data for dataset {dataset.id}")
            return file_path, 0
        fieldnames = [
            'job_id', 'source_name', 'job_type', 'status',
            'items_processed', 'items_accepted', 'items_rejected',
            'error_message', 'completed_at', 'created_at', 'data_source',
        ]
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                completed_at = getattr(row, 'completed_at', None)
                created_at = getattr(row, 'created_at', None)
                writer.writerow({
                    'job_id': row.id,
                    'source_name': getattr(row, 'source_name', ''),
                    'job_type': getattr(row, 'job_type', ''),
                    'status': getattr(row, 'status', ''),
                    'items_processed': getattr(row, 'items_processed', ''),
                    'items_accepted': getattr(row, 'items_accepted', ''),
                    'items_rejected': getattr(row, 'items_rejected', ''),
                    'error_message': getattr(row, 'error_message', '') or '',
                    'completed_at': completed_at.isoformat() if completed_at else '',
                    'created_at': created_at.isoformat() if created_at else '',
                    'data_source': 'ScrapeJob (real)',
                })
        logger.info(f"Exported {len(rows)} real scrape jobs to {file_path}")
        return file_path, len(rows)

    # -------------------------------------------------------------------------
    # Mock fallbacks (deprecated — kept for emergency use only, clearly labeled)
    # -------------------------------------------------------------------------

    def _export_mock_opportunities(self, dataset, file_path, filters):
        max_results = filters.get("max_results", 10)
        vertical = filters.get("vertical") or dataset.vertical or 'general'
        city = filters.get("city") or dataset.city or 'Unknown'
        opportunities = []
        for i in range(min(max_results, dataset.record_count or 10)):
            opportunities.append({
                'opportunity_id': f'opp-{i+1:05d}',
                'title': f'{vertical.title()} opportunity in {city} - {i+1}',
                'category': vertical, 'city': city, 'state': 'Unknown',
                'ai_opportunity_score': round(0.65 + (i * 0.02), 2),
                'market_tier': 'medium', 'trend_momentum': round(0.70 + (i * 0.01), 2),
                'competition_density': 'moderate',
                'estimated_market_size_usd': 500000 + (i * 50000),
                'estimated_startup_cost_usd': 25000 + (i * 5000),
                'estimated_monthly_revenue_usd': 15000 + (i * 2000),
                'roi_estimate_percent': round(25.0 + (i * 2), 1),
                'break_even_months': 12 - i, 'confidence_score': round(0.72 + (i * 0.01), 2),
                'data_freshness': 'simulated',
                'data_source': 'MOCK_DATA - No real data available for filters',
            })
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(opportunities[0].keys()) if opportunities else [])
            writer.writeheader()
            writer.writerows(opportunities)
        logger.warning(f"Exported {len(opportunities)} MOCK opportunities to {file_path}")
        return file_path, len(opportunities)

    def _export_mock_markets(self, dataset, file_path, filters):
        max_results = filters.get("max_results", 10)
        city = filters.get("city") or dataset.city or 'Unknown'
        markets = []
        for i in range(min(max_results, dataset.record_count or 10)):
            markets.append({
                'market_id': i + 1, 'city': city, 'state': 'Unknown', 'country': 'USA',
                'total_opportunities': 15 + (i * 3),
                'categories': json.dumps([dataset.vertical or 'general']),
                'avg_score': round(0.65 + (i * 0.01), 2), 'market_health': 'moderate',
                'data_source': 'MOCK_DATA - No real data available for filters',
            })
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(markets[0].keys()) if markets else [])
            writer.writeheader()
            writer.writerows(markets)
        logger.warning(f"Exported {len(markets)} MOCK markets to {file_path}")
        return file_path, len(markets)

    def _export_mock_trends(self, dataset, file_path, filters):
        max_results = filters.get("max_results", 10)
        vertical = filters.get("vertical") or dataset.vertical or 'general'
        trends = []
        for i in range(min(max_results, dataset.record_count or 10)):
            trends.append({
                'id': i + 1, 'trend_name': f'{vertical.title()} trend signal {i+1}',
                'trend_strength': 50 + (i * 5), 'category': vertical,
                'source_type': 'aggregated', 'opportunities_count': 10 + (i * 2),
                'growth_rate': round(1.05 + (i * 0.05), 2), 'confidence_score': 70 + (i * 2),
                'keywords': json.dumps([vertical, 'growth', 'opportunity']),
                'detected_at': datetime.utcnow().isoformat(),
                'data_source': 'MOCK_DATA - No real data available for filters',
            })
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(trends[0].keys()) if trends else [])
            writer.writeheader()
            writer.writerows(trends)
        logger.warning(f"Exported {len(trends)} MOCK trends to {file_path}")
        return file_path, len(trends)

    def _export_mock_raw_data(self, dataset, file_path, filters):
        max_results = filters.get("max_results", 20)
        raw_data = []
        for i in range(min(max_results, dataset.record_count or 20)):
            raw_data.append({
                'job_id': i + 1, 'source_name': f'Source {i+1}', 'job_type': 'scheduled',
                'status': 'completed' if i % 3 == 0 else ('pending' if i % 3 == 1 else 'failed'),
                'items_processed': 50 + (i * 5), 'items_accepted': 40 + (i * 4),
                'items_rejected': 10 + i,
                'error_message': '' if i % 3 != 2 else 'Connection timeout',
                'completed_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat(),
                'data_source': 'MOCK_DATA - No real data available for filters',
            })
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(raw_data[0].keys()) if raw_data else [])
            writer.writeheader()
            writer.writerows(raw_data)
        logger.warning(f"Exported {len(raw_data)} MOCK raw records to {file_path}")
        return file_path, len(raw_data)

    def generate_download_url(self, purchase: DatasetPurchase, file_path: str) -> str:
        storage = get_cloud_storage()
        if self.is_cloud_storage_path(file_path):
            if storage.is_configured() and storage.provider != "local":
                signed_url, error = storage.generate_signed_url(file_path, expiration_hours=24)
                if signed_url:
                    logger.info(f"Generated signed URL for purchase {purchase.id}")
                    return signed_url
                logger.warning(f"Signed URL generation failed: {error}")
        download_token = str(uuid.uuid4())
        return f"/api/v1/datasets/download/{purchase.id}?token={download_token}"

    def is_cloud_storage_path(self, file_path: str) -> bool:
        return bool(file_path and "/" in file_path and not file_path.startswith("/tmp"))

    def cleanup_expired_files(self) -> int:
        deleted_count = 0
        if not os.path.exists(self.TEMP_STORAGE_PATH):
            return deleted_count
        now = datetime.utcnow()
        for filename in os.listdir(self.TEMP_STORAGE_PATH):
            file_path = os.path.join(self.TEMP_STORAGE_PATH, filename)
            try:
                file_stat = os.stat(file_path)
                if now.timestamp() - file_stat.st_mtime > 86400:
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up file {filename}: {e}")
        return deleted_count


_delivery_service = None


def get_delivery_service() -> DatasetDeliveryService:
    global _delivery_service
    if _delivery_service is None:
        _delivery_service = DatasetDeliveryService()
    return _delivery_service
