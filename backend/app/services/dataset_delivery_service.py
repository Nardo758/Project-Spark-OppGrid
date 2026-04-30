"""Dataset delivery service - handles CSV export and download URL generation."""
import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import uuid
from sqlalchemy.orm import Session

from backend.app.models.dataset import Dataset, DatasetPurchase, DatasetType

logger = logging.getLogger(__name__)


class DatasetDeliveryService:
    """Service for generating and delivering datasets."""
    
    # Storage paths
    TEMP_STORAGE_PATH = "/tmp/dataset_exports"
    
    def __init__(self):
        """Initialize delivery service."""
        os.makedirs(self.TEMP_STORAGE_PATH, exist_ok=True)
    
    def generate_csv_file(
        self,
        dataset: Dataset,
        db: Session
    ) -> Tuple[str, int]:
        """
        Generate CSV file for a dataset.
        
        Args:
            dataset: Dataset object
            db: Database session
            
        Returns:
            Tuple of (file_path, row_count)
        """
        file_path = os.path.join(
            self.TEMP_STORAGE_PATH,
            f"{dataset.id}_{datetime.utcnow().isoformat()}.csv"
        )
        
        if dataset.dataset_type == DatasetType.OPPORTUNITIES:
            return self._export_opportunities(dataset, file_path, db)
        elif dataset.dataset_type == DatasetType.MARKETS:
            return self._export_markets(dataset, file_path, db)
        elif dataset.dataset_type == DatasetType.TRENDS:
            return self._export_trends(dataset, file_path, db)
        elif dataset.dataset_type == DatasetType.RAW_DATA:
            return self._export_raw_data(dataset, file_path, db)
        else:
            raise ValueError(f"Unknown dataset type: {dataset.dataset_type}")
    
    def _export_opportunities(
        self,
        dataset: Dataset,
        file_path: str,
        db: Session
    ) -> Tuple[str, int]:
        """
        Export opportunities dataset to CSV.
        
        Schema: id, title, vertical, city, success_probability, confidence, 
                risk_profile, market_health, trend_momentum, reasoning
        """
        # Mock data generation - in production, would query actual data
        opportunities = self._generate_mock_opportunities(dataset)
        
        fieldnames = [
            'id', 'title', 'vertical', 'city', 'success_probability',
            'confidence', 'risk_profile', 'market_health', 'trend_momentum', 'reasoning'
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(opportunities)
        
        logger.info(f"Exported {len(opportunities)} opportunities to {file_path}")
        return file_path, len(opportunities)
    
    def _export_markets(
        self,
        dataset: Dataset,
        file_path: str,
        db: Session
    ) -> Tuple[str, int]:
        """
        Export markets dataset to CSV.
        
        Schema: vertical, city, market_health_score, saturation_level, 
                demand_vs_supply, business_count, growth_rate, confidence
        """
        markets = self._generate_mock_markets(dataset)
        
        fieldnames = [
            'vertical', 'city', 'market_health_score', 'saturation_level',
            'demand_vs_supply', 'business_count', 'growth_rate', 'confidence'
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(markets)
        
        logger.info(f"Exported {len(markets)} markets to {file_path}")
        return file_path, len(markets)
    
    def _export_trends(
        self,
        dataset: Dataset,
        file_path: str,
        db: Session
    ) -> Tuple[str, int]:
        """
        Export trends dataset to CSV.
        
        Schema: trend_name, vertical, acceleration_factor, direction, 
                signal_count, confidence, top_cities
        """
        trends = self._generate_mock_trends(dataset)
        
        fieldnames = [
            'trend_name', 'vertical', 'acceleration_factor', 'direction',
            'signal_count', 'confidence', 'top_cities'
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trends)
        
        logger.info(f"Exported {len(trends)} trends to {file_path}")
        return file_path, len(trends)
    
    def _export_raw_data(
        self,
        dataset: Dataset,
        file_path: str,
        db: Session
    ) -> Tuple[str, int]:
        """
        Export raw data dataset to CSV.
        
        Schema: source_type, external_id, title, description, processed, 
                received_at, observed_at
        """
        raw_data = self._generate_mock_raw_data(dataset)
        
        fieldnames = [
            'source_type', 'external_id', 'title', 'description', 'processed',
            'received_at', 'observed_at'
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(raw_data)
        
        logger.info(f"Exported {len(raw_data)} raw data records to {file_path}")
        return file_path, len(raw_data)
    
    # Mock data generation methods
    
    def _generate_mock_opportunities(self, dataset: Dataset) -> List[Dict[str, Any]]:
        """Generate mock opportunities data."""
        opportunities = []
        for i in range(min(10, dataset.record_count)):
            opportunities.append({
                'id': f'opp-{i+1:05d}',
                'title': f'Opportunity in {dataset.vertical or "market"} - {i+1}',
                'vertical': dataset.vertical or 'tech',
                'city': dataset.city or 'San Francisco',
                'success_probability': 0.65 + (i * 0.02),
                'confidence': 0.72 + (i * 0.01),
                'risk_profile': 'medium' if i % 3 == 0 else ('low' if i % 3 == 1 else 'high'),
                'market_health': 0.78,
                'trend_momentum': 0.82,
                'reasoning': f'Strong market indicators and growth trajectory in {dataset.city or "the target market"}',
            })
        return opportunities
    
    def _generate_mock_markets(self, dataset: Dataset) -> List[Dict[str, Any]]:
        """Generate mock markets data."""
        markets = []
        cities = [dataset.city or 'San Francisco', 'New York', 'Austin', 'Los Angeles']
        verticals = [dataset.vertical or 'coffee', 'restaurants', 'retail', 'tech']
        
        for city in cities[:min(3, len(cities))]:
            for vertical in verticals[:min(3, len(verticals))]:
                markets.append({
                    'vertical': vertical,
                    'city': city,
                    'market_health_score': 0.72 + (len(markets) * 0.01),
                    'saturation_level': 0.55,
                    'demand_vs_supply': 1.2,
                    'business_count': 45 + (len(markets) * 5),
                    'growth_rate': 0.085,
                    'confidence': 0.78,
                })
        return markets
    
    def _generate_mock_trends(self, dataset: Dataset) -> List[Dict[str, Any]]:
        """Generate mock trends data."""
        trends = []
        trend_names = [
            'Sustainability focus in business',
            'Remote work adoption',
            'AI integration in operations',
            'Direct-to-consumer expansion',
            'Data-driven decision making',
        ]
        
        for trend in trend_names[:min(10, dataset.record_count)]:
            trends.append({
                'trend_name': trend,
                'vertical': dataset.vertical or 'general',
                'acceleration_factor': 1.15 + (len(trends) * 0.05),
                'direction': 'up' if len(trends) % 2 == 0 else 'stable',
                'signal_count': 45 + (len(trends) * 3),
                'confidence': 0.78,
                'top_cities': 'San Francisco, New York, Austin',
            })
        return trends
    
    def _generate_mock_raw_data(self, dataset: Dataset) -> List[Dict[str, Any]]:
        """Generate mock raw data."""
        raw_data = []
        for i in range(min(20, dataset.record_count)):
            raw_data.append({
                'source_type': 'google_maps' if i % 3 == 0 else ('web_scrape' if i % 3 == 1 else 'api'),
                'external_id': f'ext-{i+1:06d}',
                'title': f'Data point {i+1}',
                'description': f'Raw data record from {dataset.city or "market"}',
                'processed': 'true' if i % 2 == 0 else 'false',
                'received_at': (datetime.utcnow() - timedelta(days=i)).isoformat(),
                'observed_at': (datetime.utcnow() - timedelta(days=i+1)).isoformat(),
            })
        return raw_data
    
    def generate_download_url(
        self,
        purchase: DatasetPurchase,
        file_path: str
    ) -> str:
        """
        Generate a signed download URL for a dataset.
        
        In production, this would use cloud storage (S3, GCS, Azure Blob).
        For now, we return a local file reference with expiration.
        
        Args:
            purchase: DatasetPurchase object
            file_path: Path to the CSV file
            
        Returns:
            Download URL (for now, file path reference with token)
        """
        # Create a download token for tracking
        download_token = str(uuid.uuid4())
        
        # In production, upload to cloud storage and get signed URL
        # For development, return a local reference
        download_url = f"/api/v1/datasets/download/{purchase.id}?token={download_token}"
        
        logger.info(f"Generated download URL for purchase {purchase.id}")
        return download_url
    
    def cleanup_expired_files(self) -> int:
        """
        Clean up expired dataset files from temporary storage.
        
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        if not os.path.exists(self.TEMP_STORAGE_PATH):
            return deleted_count
        
        now = datetime.utcnow()
        for filename in os.listdir(self.TEMP_STORAGE_PATH):
            file_path = os.path.join(self.TEMP_STORAGE_PATH, filename)
            
            # Check file age - delete if older than 24 hours
            try:
                file_stat = os.stat(file_path)
                file_age = now.timestamp() - file_stat.st_mtime
                
                if file_age > 86400:  # 24 hours
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted expired file: {filename}")
            except Exception as e:
                logger.error(f"Error cleaning up file {filename}: {e}")
        
        return deleted_count


# Singleton instance
_delivery_service = None


def get_delivery_service() -> DatasetDeliveryService:
    """Get or create the delivery service singleton."""
    global _delivery_service
    if _delivery_service is None:
        _delivery_service = DatasetDeliveryService()
    return _delivery_service
