"""
Land Use Code Mappings

Maps NAICS industry codes to land use codes per municipal jurisdiction.
Each metro may have different property classification systems.

Land Use Code Discovery Sources:
- Miami-Dade: DOR (Department of Revenue) code 39 = "Warehousing and Storage"
- Chicago: Land use code 516 = "Mini Warehouse Storage" 
- NYC: PLUTO dataset bldg_class D4 (Storage), E0-E2 (Warehouse)
- Seattle: Verify via municipal docs
- Denver: Verify via municipal docs
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class LandUseMappingError(Exception):
    """Raised when land use codes cannot be determined"""
    pass


class LandUseMapping:
    """
    Manages land use code mappings across different municipalities.
    
    Each metro has its own property classification system. This service
    translates industry codes to the correct codes for each metro.
    """
    
    # Comprehensive mapping of industry → metro → land use codes
    INDUSTRY_MAPPINGS = {
        "self-storage": {
            "miami": {
                "state": "FL",
                "codes": ["39"],  # DOR code 39: Warehousing and Storage
                "description": "Self-storage facilities, mini-warehouses, storage units",
                "field_name": "dor_code",  # Miami-Dade uses DOR codes
                "verified": True,
                "notes": "DOR code 39 includes all warehousing/storage. Query by this code.",
                "data_source": "Miami-Dade DOR Classification System",
            },
            "chicago": {
                "state": "IL",
                "codes": ["516"],  # Chicago land use code 516
                "description": "Mini warehouse storage facilities",
                "field_name": "land_use_code",
                "verified": True,
                "notes": "Land use code 516 = Mini Warehouse Storage. Chicago has detailed classification.",
                "data_source": "City of Chicago Land Use Classification",
            },
            "nyc": {
                "state": "NY",
                "codes": ["D4", "E0", "E1", "E2"],  # PLUTO building classes
                "description": "D4 (Storage), E0-E2 (Warehouse/Industrial)",
                "field_name": "bldg_class",  # NYC PLUTO dataset
                "verified": True,
                "notes": "NYC PLUTO: D4=Storage, E0=Warehouse, E1=Factory, E2=Industrial",
                "data_source": "NYC PLUTO Property Use Code Classification",
            },
            "seattle": {
                "state": "WA",
                "codes": ["WM"],  # Warehouse/Manufacturing
                "description": "Warehouse and storage facilities",
                "field_name": "land_use_code",
                "verified": False,  # Needs verification
                "notes": "Seattle uses land_use_code. WM (Warehouse/Manufacturing) likely includes storage.",
                "data_source": "City of Seattle Comprehensive Plan Land Use",
            },
            "denver": {
                "state": "CO",
                "codes": ["U3"],  # Warehouse/Manufacturing
                "description": "Warehouse and self-storage facilities",
                "field_name": "zoning_code",
                "verified": False,  # Needs verification
                "notes": "Denver zoning: U3 likely covers warehouse/storage. Verify with city.",
                "data_source": "City and County of Denver Zoning Code",
            },
            "atlanta": {
                "state": "GA",
                "codes": ["V100", "V200"],  # Wholesale/Warehouse
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Atlanta Socrata uses use_code. V100/V200 = Wholesale/Storage.",
                "data_source": "City of Atlanta Assessor Data",
            },
            "boston": {
                "state": "MA",
                "codes": ["1001", "1002"],  # Industrial/Storage
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Boston uses use_code for industrial and storage.",
                "data_source": "City of Boston Property Database",
            },
            "dallas": {
                "state": "TX",
                "codes": ["0304"],  # Warehouse/Storage
                "description": "Warehouse and self-storage facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Dallas CAD uses 0304 for warehouse/storage facilities.",
                "data_source": "Dallas Central Appraisal District",
            },
            "houston": {
                "state": "TX",
                "codes": ["0304"],  # Warehouse/Storage
                "description": "Warehouse and self-storage facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Harris County uses 0304 for warehouse/storage.",
                "data_source": "Harris County Appraisal District",
            },
            "los_angeles": {
                "state": "CA",
                "codes": ["1210", "1211"],  # Industrial/Warehouse
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "LA County Assessor uses 1210/1211 for warehousing.",
                "data_source": "Los Angeles County Assessor",
            },
            "phoenix": {
                "state": "AZ",
                "codes": ["0304"],  # Warehouse/Storage
                "description": "Warehouse and self-storage facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Maricopa County uses 0304 for warehouse/storage.",
                "data_source": "Maricopa County Assessor",
            },
            "san_francisco": {
                "state": "CA",
                "codes": ["WMUH", "INDL"],  # Warehouse/Industrial
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "SF uses WMUH (Warehouse) and INDL (Industrial).",
                "data_source": "San Francisco Assessor-Recorder",
            },
            "san_diego": {
                "state": "CA",
                "codes": ["1200", "1210"],  # Industrial/Warehouse
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "San Diego County uses 1200/1210 for industrial/warehouse.",
                "data_source": "San Diego County Assessor",
            },
            "washington_dc": {
                "state": "DC",
                "codes": ["IA10", "IA20"],  # Industrial
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "DC uses IA10/IA20 for industrial/warehouse.",
                "data_source": "DC Office of the Assessor",
            },
            "austin": {
                "state": "TX",
                "codes": ["0304"],  # Warehouse/Storage
                "description": "Warehouse and self-storage facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Travis County CAD uses 0304 for warehouse/storage.",
                "data_source": "Travis County Appraisal District",
            },
            "charlotte": {
                "state": "NC",
                "codes": ["0920", "0930"],  # Industrial/Warehouse
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Mecklenburg County uses 0920/0930 for industrial/warehouse.",
                "data_source": "Mecklenburg County Tax Assessor",
            },
            "nashville": {
                "state": "TN",
                "codes": ["0306"],  # Industrial/Warehouse
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Davidson County uses 0306 for industrial/warehouse.",
                "data_source": "Davidson County Assessor",
            },
            "portland": {
                "state": "OR",
                "codes": ["M", "I"],  # Manufacturing/Industrial
                "description": "Warehouse and self-storage facilities",
                "field_name": "zoning_code",
                "verified": False,
                "notes": "Portland uses M (Manufacturing) or I (Industrial) zones.",
                "data_source": "Multnomah County Assessor",
            },
            "tampa": {
                "state": "FL",
                "codes": ["0409", "0410"],  # Warehouse/Storage
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Hillsborough County uses 0409/0410 for warehouse/storage.",
                "data_source": "Hillsborough County Property Appraiser",
            },
            "philadelphia": {
                "state": "PA",
                "codes": ["0660", "0670"],  # Industrial/Warehouse
                "description": "Warehouse and self-storage facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Philadelphia uses 0660/0670 for industrial/warehouse.",
                "data_source": "Philadelphia Office of Property Assessment",
            },
        },
    }
    
    # Census population data for each metro (2020 Census or latest available)
    METRO_POPULATIONS = {
        ("miami", "FL"): 6_091_747,  # Miami-Dade metro
        ("chicago", "IL"): 9_618_502,  # Chicago metro
        ("nyc", "NY"): 20_201_249,  # NYC metro
        ("seattle", "WA"): 4_018_762,  # Seattle metro
        ("denver", "CO"): 3_154_794,  # Denver metro
        ("atlanta", "GA"): 6_089_815,  # Atlanta metro
        ("boston", "MA"): 4_941_632,  # Boston metro
        ("dallas", "TX"): 8_104_348,  # Dallas-Fort Worth metro
        ("houston", "TX"): 7_553_763,  # Houston metro
        ("los_angeles", "CA"): 13_200_998,  # Los Angeles metro
        ("phoenix", "AZ"): 5_049_417,  # Phoenix metro
        ("san_francisco", "CA"): 4_748_162,  # San Francisco Bay Area
        ("san_diego", "CA"): 3_338_330,  # San Diego metro
        ("washington_dc", "DC"): 6_341_767,  # Washington DC metro
        ("austin", "TX"): 2_295_303,  # Austin metro
        ("charlotte", "NC"): 2_660_329,  # Charlotte metro
        ("nashville", "TN"): 1_989_519,  # Nashville metro
        ("portland", "OR"): 2_537_189,  # Portland metro
        ("tampa", "FL"): 3_280_130,  # Tampa metro
        ("philadelphia", "PA"): 6_245_051,  # Philadelphia metro
    }
    
    @classmethod
    def get_land_use_codes(
        cls,
        industry: str,
        metro: str,
        state: str = None
    ) -> List[str]:
        """
        Get land use codes for an industry in a specific metro.
        
        Args:
            industry: Industry code (e.g., "self-storage")
            metro: Metro name (e.g., "miami", "chicago")
            state: Optional state code for validation
        
        Returns:
            List of land use codes
        
        Raises:
            LandUseMappingError: If industry/metro combination not found
        """
        industry_lower = industry.lower()
        metro_lower = metro.lower()
        
        if industry_lower not in cls.INDUSTRY_MAPPINGS:
            raise LandUseMappingError(
                f"Industry '{industry}' not supported. "
                f"Supported: {list(cls.INDUSTRY_MAPPINGS.keys())}"
            )
        
        metro_map = cls.INDUSTRY_MAPPINGS[industry_lower]
        
        if metro_lower not in metro_map:
            raise LandUseMappingError(
                f"Metro '{metro}' not configured for industry '{industry}'. "
                f"Supported metros: {list(metro_map.keys())}"
            )
        
        metro_config = metro_map[metro_lower]
        
        # Validate state if provided
        if state and state.upper() != metro_config["state"].upper():
            logger.warning(
                f"State mismatch: provided {state}, expected {metro_config['state']}"
            )
        
        return metro_config["codes"]
    
    @classmethod
    def get_metro_config(cls, industry: str, metro: str) -> Dict:
        """
        Get full configuration for an industry/metro combination.
        
        Returns: {
            'codes': [...],
            'field_name': 'land_use_code',
            'verified': True/False,
            'notes': '...',
            'data_source': '...',
        }
        """
        industry_lower = industry.lower()
        metro_lower = metro.lower()
        
        if industry_lower not in cls.INDUSTRY_MAPPINGS:
            raise LandUseMappingError(f"Industry '{industry}' not supported")
        
        metro_map = cls.INDUSTRY_MAPPINGS[industry_lower]
        
        if metro_lower not in metro_map:
            raise LandUseMappingError(
                f"Metro '{metro}' not configured for industry '{industry}'"
            )
        
        return metro_map[metro_lower]
    
    @classmethod
    def get_population(cls, metro: str, state: str) -> int:
        """
        Get population for a metro.
        
        Args:
            metro: Metro name
            state: State code
        
        Returns:
            Population integer
        
        Raises:
            LandUseMappingError: If metro not found
        """
        key = (metro.lower(), state.upper())
        
        if key not in cls.METRO_POPULATIONS:
            raise LandUseMappingError(
                f"Population not available for {metro}, {state}. "
                f"Available metros: {list(cls.METRO_POPULATIONS.keys())}"
            )
        
        return cls.METRO_POPULATIONS[key]
    
    @classmethod
    def list_supported_metros(cls, industry: str = None) -> List[str]:
        """
        List all supported metros, optionally filtered by industry.
        
        Args:
            industry: Optional industry filter
        
        Returns:
            List of metro names
        """
        if not industry:
            # Return all unique metros across all industries
            metros = set()
            for industry_map in cls.INDUSTRY_MAPPINGS.values():
                metros.update(industry_map.keys())
            return sorted(list(metros))
        
        industry_lower = industry.lower()
        if industry_lower not in cls.INDUSTRY_MAPPINGS:
            return []
        
        return sorted(list(cls.INDUSTRY_MAPPINGS[industry_lower].keys()))
    
    @classmethod
    def list_supported_industries(cls) -> List[str]:
        """List all supported industries"""
        return list(cls.INDUSTRY_MAPPINGS.keys())
    
    @classmethod
    def is_configured(cls, industry: str, metro: str) -> bool:
        """Check if an industry/metro combination is configured"""
        try:
            cls.get_land_use_codes(industry, metro)
            return True
        except LandUseMappingError:
            return False
    
    @classmethod
    def is_verified(cls, industry: str, metro: str) -> bool:
        """Check if an industry/metro mapping has been verified"""
        try:
            config = cls.get_metro_config(industry, metro)
            return config.get("verified", False)
        except LandUseMappingError:
            return False


# Benchmark values for supply analysis
SUPPLY_BENCHMARKS = {
    "self-storage": {
        "sqft_per_capita_benchmark": 7.0,  # Industry standard
        "oversaturated_threshold": 7.0,  # > 7.0
        "balanced_min": 5.0,  # 5.0-7.0
        "balanced_max": 7.0,
        "undersaturated_threshold": 5.0,  # < 5.0
    }
}


def get_benchmark(industry: str) -> Dict:
    """Get supply benchmark for an industry"""
    industry_lower = industry.lower()
    if industry_lower not in SUPPLY_BENCHMARKS:
        logger.warning(f"No benchmark found for industry '{industry}', using default")
        return {
            "sqft_per_capita_benchmark": 7.0,
            "oversaturated_threshold": 7.0,
            "balanced_min": 5.0,
            "balanced_max": 7.0,
            "undersaturated_threshold": 5.0,
        }
    return SUPPLY_BENCHMARKS[industry_lower]
