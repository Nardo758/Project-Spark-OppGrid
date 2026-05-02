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
        "restaurant": {
            "miami": {
                "state": "FL",
                "codes": ["31"],  # DOR code 31: Food Service
                "description": "Restaurants, cafes, food service facilities",
                "field_name": "dor_code",
                "verified": True,
                "notes": "DOR code 31 includes restaurants and food service.",
                "data_source": "Miami-Dade DOR Classification System",
            },
            "chicago": {
                "state": "IL",
                "codes": ["560"],  # Chicago land use code 560
                "description": "Restaurant and food service facilities",
                "field_name": "land_use_code",
                "verified": True,
                "notes": "Land use code 560 = Food Service.",
                "data_source": "City of Chicago Land Use Classification",
            },
            "nyc": {
                "state": "NY",
                "codes": ["G8", "G9"],  # PLUTO building classes
                "description": "Restaurants and food service",
                "field_name": "bldg_class",
                "verified": True,
                "notes": "NYC PLUTO: G8=Restaurant, G9=Bar/Nightclub",
                "data_source": "NYC PLUTO Property Use Code Classification",
            },
            "denver": {
                "state": "CO",
                "codes": ["HR"],  # Hotel/Restaurant
                "description": "Restaurants and food service",
                "field_name": "zoning_code",
                "verified": False,
                "notes": "Denver uses HR (Hotel/Restaurant) zones.",
                "data_source": "City and County of Denver Zoning Code",
            },
            "atlanta": {
                "state": "GA",
                "codes": ["V400"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Atlanta uses V400 for food service.",
                "data_source": "City of Atlanta Assessor Data",
            },
            "seattle": {
                "state": "WA",
                "codes": ["C"],  # Commercial/Food Service
                "description": "Restaurants and food service",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Seattle uses C (Commercial) zones.",
                "data_source": "City of Seattle Comprehensive Plan Land Use",
            },
            "boston": {
                "state": "MA",
                "codes": ["3000", "3001"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Boston uses 3000/3001 for food service.",
                "data_source": "City of Boston Property Database",
            },
            "dallas": {
                "state": "TX",
                "codes": ["0314"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Dallas CAD uses 0314 for food service.",
                "data_source": "Dallas Central Appraisal District",
            },
            "houston": {
                "state": "TX",
                "codes": ["0314"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Harris County uses 0314 for food service.",
                "data_source": "Harris County Appraisal District",
            },
            "los_angeles": {
                "state": "CA",
                "codes": ["1300", "1310"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "LA County uses 1300/1310 for food service.",
                "data_source": "Los Angeles County Assessor",
            },
            "phoenix": {
                "state": "AZ",
                "codes": ["0314"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Maricopa County uses 0314 for food service.",
                "data_source": "Maricopa County Assessor",
            },
            "san_francisco": {
                "state": "CA",
                "codes": ["RES", "REST"],  # Restaurant/Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "SF uses RES (Restaurant) and REST zones.",
                "data_source": "San Francisco Assessor-Recorder",
            },
            "san_diego": {
                "state": "CA",
                "codes": ["1301", "1302"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "San Diego County uses 1301/1302 for food service.",
                "data_source": "San Diego County Assessor",
            },
            "washington_dc": {
                "state": "DC",
                "codes": ["CA20"],  # Commercial/Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "DC uses CA20 for food service.",
                "data_source": "DC Office of the Assessor",
            },
            "austin": {
                "state": "TX",
                "codes": ["0314"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Travis County CAD uses 0314 for food service.",
                "data_source": "Travis County Appraisal District",
            },
            "charlotte": {
                "state": "NC",
                "codes": ["1001"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Mecklenburg County uses 1001 for food service.",
                "data_source": "Mecklenburg County Tax Assessor",
            },
            "nashville": {
                "state": "TN",
                "codes": ["0400"],  # Commercial/Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Davidson County uses 0400 for commercial food service.",
                "data_source": "Davidson County Assessor",
            },
            "portland": {
                "state": "OR",
                "codes": ["C", "CO"],  # Commercial/Office
                "description": "Restaurants and food service facilities",
                "field_name": "zoning_code",
                "verified": False,
                "notes": "Portland uses C (Commercial) zones.",
                "data_source": "Multnomah County Assessor",
            },
            "tampa": {
                "state": "FL",
                "codes": ["0406"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Hillsborough County uses 0406 for food service.",
                "data_source": "Hillsborough County Property Appraiser",
            },
            "philadelphia": {
                "state": "PA",
                "codes": ["0630"],  # Food Service
                "description": "Restaurants and food service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Philadelphia uses 0630 for food service.",
                "data_source": "Philadelphia Office of Property Assessment",
            },
        },
        "fitness": {
            "miami": {
                "state": "FL",
                "codes": ["30"],  # DOR code 30: Recreation/Fitness
                "description": "Fitness studios, gymnasiums, health clubs",
                "field_name": "dor_code",
                "verified": True,
                "notes": "DOR code 30 includes fitness facilities and recreation.",
                "data_source": "Miami-Dade DOR Classification System",
            },
            "denver": {
                "state": "CO",
                "codes": ["H2"],  # Health/Fitness
                "description": "Fitness studios, gymnasiums, health clubs",
                "field_name": "zoning_code",
                "verified": False,
                "notes": "Denver uses H2 (Health/Fitness) zones.",
                "data_source": "City and County of Denver Zoning Code",
            },
            "chicago": {
                "state": "IL",
                "codes": ["566"],  # Chicago land use code 566
                "description": "Fitness and recreation facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Land use code 566 = Recreation/Fitness.",
                "data_source": "City of Chicago Land Use Classification",
            },
            "nyc": {
                "state": "NY",
                "codes": ["G0", "G1"],  # PLUTO building classes
                "description": "Fitness and recreation facilities",
                "field_name": "bldg_class",
                "verified": False,
                "notes": "NYC PLUTO: G0/G1 = Recreation/Fitness",
                "data_source": "NYC PLUTO Property Use Code Classification",
            },
            "atlanta": {
                "state": "GA",
                "codes": ["V300"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "Atlanta uses V300 for recreation/fitness.",
                "data_source": "City of Atlanta Assessor Data",
            },
            "seattle": {
                "state": "WA",
                "codes": ["R"],  # Recreation
                "description": "Fitness studios and health clubs",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Seattle uses R (Recreation) zones.",
                "data_source": "City of Seattle Comprehensive Plan Land Use",
            },
            "boston": {
                "state": "MA",
                "codes": ["3400", "3401"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "Boston uses 3400/3401 for fitness.",
                "data_source": "City of Boston Property Database",
            },
            "dallas": {
                "state": "TX",
                "codes": ["0319"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Dallas CAD uses 0319 for fitness.",
                "data_source": "Dallas Central Appraisal District",
            },
            "houston": {
                "state": "TX",
                "codes": ["0319"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Harris County uses 0319 for fitness.",
                "data_source": "Harris County Appraisal District",
            },
            "los_angeles": {
                "state": "CA",
                "codes": ["1500", "1510"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "LA County uses 1500/1510 for fitness.",
                "data_source": "Los Angeles County Assessor",
            },
            "phoenix": {
                "state": "AZ",
                "codes": ["0319"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Maricopa County uses 0319 for fitness.",
                "data_source": "Maricopa County Assessor",
            },
            "san_francisco": {
                "state": "CA",
                "codes": ["REC", "HLTH"],  # Recreation/Health
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "SF uses REC/HLTH codes for fitness.",
                "data_source": "San Francisco Assessor-Recorder",
            },
            "san_diego": {
                "state": "CA",
                "codes": ["1501", "1502"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "San Diego County uses 1501/1502 for fitness.",
                "data_source": "San Diego County Assessor",
            },
            "washington_dc": {
                "state": "DC",
                "codes": ["CA30"],  # Commercial/Recreation
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "DC uses CA30 for recreation/fitness.",
                "data_source": "DC Office of the Assessor",
            },
            "austin": {
                "state": "TX",
                "codes": ["0319"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Travis County CAD uses 0319 for fitness.",
                "data_source": "Travis County Appraisal District",
            },
            "charlotte": {
                "state": "NC",
                "codes": ["1100"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "Mecklenburg County uses 1100 for fitness.",
                "data_source": "Mecklenburg County Tax Assessor",
            },
            "nashville": {
                "state": "TN",
                "codes": ["0410"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "Davidson County uses 0410 for fitness.",
                "data_source": "Davidson County Assessor",
            },
            "portland": {
                "state": "OR",
                "codes": ["R", "REC"],  # Recreation
                "description": "Fitness studios and health clubs",
                "field_name": "zoning_code",
                "verified": False,
                "notes": "Portland uses R/REC zones for recreation.",
                "data_source": "Multnomah County Assessor",
            },
            "tampa": {
                "state": "FL",
                "codes": ["0411"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "Hillsborough County uses 0411 for fitness.",
                "data_source": "Hillsborough County Property Appraiser",
            },
            "philadelphia": {
                "state": "PA",
                "codes": ["0650"],  # Recreation/Fitness
                "description": "Fitness studios and health clubs",
                "field_name": "use_code",
                "verified": False,
                "notes": "Philadelphia uses 0650 for fitness.",
                "data_source": "Philadelphia Office of Property Assessment",
            },
        },
        "gas_station": {
            "miami": {
                "state": "FL",
                "codes": ["32"],  # DOR code 32: Gas Stations
                "description": "Gas stations and fuel facilities",
                "field_name": "dor_code",
                "verified": True,
                "notes": "DOR code 32 = Gas Stations/Service Stations.",
                "data_source": "Miami-Dade DOR Classification System",
            },
            "chicago": {
                "state": "IL",
                "codes": ["562"],  # Chicago land use code 562
                "description": "Gas stations and vehicle service",
                "field_name": "land_use_code",
                "verified": True,
                "notes": "Land use code 562 = Gas Stations.",
                "data_source": "City of Chicago Land Use Classification",
            },
            "nyc": {
                "state": "NY",
                "codes": ["G2", "G3"],  # PLUTO building classes
                "description": "Gas stations and service stations",
                "field_name": "bldg_class",
                "verified": False,
                "notes": "NYC PLUTO: G2/G3 = Service Stations",
                "data_source": "NYC PLUTO Property Use Code Classification",
            },
            "atlanta": {
                "state": "GA",
                "codes": ["V200"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Atlanta uses V200 for service stations.",
                "data_source": "City of Atlanta Assessor Data",
            },
            "denver": {
                "state": "CO",
                "codes": ["U4"],  # Service/Gas Station
                "description": "Gas stations and service facilities",
                "field_name": "zoning_code",
                "verified": False,
                "notes": "Denver uses U4 for service/gas stations.",
                "data_source": "City and County of Denver Zoning Code",
            },
            "seattle": {
                "state": "WA",
                "codes": ["CM"],  # Commercial/Mixed
                "description": "Gas stations and service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Seattle uses CM zones.",
                "data_source": "City of Seattle Comprehensive Plan Land Use",
            },
            "boston": {
                "state": "MA",
                "codes": ["3200", "3201"],  # Service/Gas Stations
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Boston uses 3200/3201 for service stations.",
                "data_source": "City of Boston Property Database",
            },
            "dallas": {
                "state": "TX",
                "codes": ["0312"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Dallas CAD uses 0312 for service stations.",
                "data_source": "Dallas Central Appraisal District",
            },
            "houston": {
                "state": "TX",
                "codes": ["0312"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Harris County uses 0312 for service stations.",
                "data_source": "Harris County Appraisal District",
            },
            "los_angeles": {
                "state": "CA",
                "codes": ["1100", "1110"],  # Service/Auto
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "LA County uses 1100/1110 for service facilities.",
                "data_source": "Los Angeles County Assessor",
            },
            "phoenix": {
                "state": "AZ",
                "codes": ["0312"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Maricopa County uses 0312 for service stations.",
                "data_source": "Maricopa County Assessor",
            },
            "san_francisco": {
                "state": "CA",
                "codes": ["SVC", "GAS"],  # Service/Gas
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "SF uses SVC/GAS codes for service stations.",
                "data_source": "San Francisco Assessor-Recorder",
            },
            "san_diego": {
                "state": "CA",
                "codes": ["1101", "1102"],  # Service/Auto
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "San Diego County uses 1101/1102 for service.",
                "data_source": "San Diego County Assessor",
            },
            "washington_dc": {
                "state": "DC",
                "codes": ["CA40"],  # Commercial/Service
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "DC uses CA40 for service stations.",
                "data_source": "DC Office of the Assessor",
            },
            "austin": {
                "state": "TX",
                "codes": ["0312"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "land_use_code",
                "verified": False,
                "notes": "Travis County CAD uses 0312 for service stations.",
                "data_source": "Travis County Appraisal District",
            },
            "charlotte": {
                "state": "NC",
                "codes": ["1200"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Mecklenburg County uses 1200 for service stations.",
                "data_source": "Mecklenburg County Tax Assessor",
            },
            "nashville": {
                "state": "TN",
                "codes": ["0450"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Davidson County uses 0450 for service stations.",
                "data_source": "Davidson County Assessor",
            },
            "portland": {
                "state": "OR",
                "codes": ["S", "SM"],  # Service/Mixed
                "description": "Gas stations and service facilities",
                "field_name": "zoning_code",
                "verified": False,
                "notes": "Portland uses S/SM zones for service.",
                "data_source": "Multnomah County Assessor",
            },
            "tampa": {
                "state": "FL",
                "codes": ["0408"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Hillsborough County uses 0408 for service stations.",
                "data_source": "Hillsborough County Property Appraiser",
            },
            "philadelphia": {
                "state": "PA",
                "codes": ["0640"],  # Service Stations
                "description": "Gas stations and service facilities",
                "field_name": "use_code",
                "verified": False,
                "notes": "Philadelphia uses 0640 for service stations.",
                "data_source": "Philadelphia Office of Property Assessment",
            },
        },
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
    },
    "restaurant": {
        "seats_per_1k_benchmark": 40.0,  # Industry standard
        "oversaturated_threshold": 50.0,  # > 50 seats/1k
        "balanced_min": 30.0,  # 30-50 seats/1k
        "balanced_max": 50.0,
        "undersaturated_threshold": 30.0,  # < 30 seats/1k
    },
    "fitness": {
        "sqft_per_capita_benchmark": 10.0,  # Industry standard
        "oversaturated_threshold": 10.0,  # > 10.0
        "balanced_min": 6.0,  # 6.0-10.0
        "balanced_max": 10.0,
        "undersaturated_threshold": 6.0,  # < 6.0
    },
    "gas_station": {
        "vehicles_per_station_benchmark": 500.0,  # Industry standard
        "oversaturated_threshold": 400.0,  # < 400 (too many stations)
        "balanced_min": 400.0,  # 400-600 vehicles/station
        "balanced_max": 600.0,
        "undersaturated_threshold": 600.0,  # > 600 (too few stations)
    },
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
