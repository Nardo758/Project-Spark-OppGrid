"""
Map Snippet Generator - Creates map visualizations for PDF reports
Uses static map generation with pin overlays and context
"""

import io
import logging
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlencode
import requests
from PIL import Image, ImageDraw, ImageFont
import base64

logger = logging.getLogger(__name__)


class MapSnippetGenerator:
    """Generate map snippets for embedding in PDF reports"""

    # Static map service (Google Maps Static API or similar)
    STATIC_MAP_API = "https://maps.googleapis.com/maps/api/staticmap"
    
    # Default map parameters
    DEFAULT_WIDTH = 400
    DEFAULT_HEIGHT = 300
    DEFAULT_ZOOM = 13
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize map generator
        
        Args:
            api_key: Google Maps API key (optional, can use free tier for basic maps)
        """
        self.api_key = api_key
    
    def generate_candidate_map(
        self,
        candidate_name: str,
        latitude: float,
        longitude: float,
        markers: Optional[List[Dict[str, Any]]] = None,
        context_radius_miles: float = 1.0,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        zoom: int = DEFAULT_ZOOM,
    ) -> bytes:
        """
        Generate a map snippet for a single candidate location
        
        Args:
            candidate_name: Name of the candidate/location
            latitude: Latitude of main candidate
            longitude: Longitude of main candidate
            markers: Optional list of other markers {'lat', 'lng', 'label'}
            context_radius_miles: Radius for context (not used in static map but for reference)
            width: Map width in pixels
            height: Map height in pixels
            zoom: Zoom level (13 is good for city-level)
        
        Returns:
            PNG image bytes of map
        """
        try:
            # Build marker string for primary candidate
            marker_str = f"color:0x0066CC|label:A|{latitude},{longitude}"
            
            # Add additional markers if provided
            if markers:
                for idx, marker in enumerate(markers[:4], start=1):  # Limit to 5 total
                    label = chr(65 + idx)  # B, C, D, etc.
                    marker_str += f"&markers=color:0xFF6B35|label:{label}|{marker.get('lat')},{marker.get('lng')}"
            
            # Build map parameters
            params = {
                'center': f"{latitude},{longitude}",
                'zoom': zoom,
                'size': f"{width}x{height}",
                'markers': marker_str,
                'style': self._get_map_style(),
                'scale': '1',
                'format': 'png',
            }
            
            if self.api_key:
                params['key'] = self.api_key
            
            # Request static map
            response = requests.get(self.STATIC_MAP_API, params=params, timeout=5)
            response.raise_for_status()
            
            # Add title overlay to map image
            map_image = Image.open(io.BytesIO(response.content))
            return self._add_map_title(map_image, candidate_name)
            
        except Exception as e:
            logger.error(f"Failed to generate map for {candidate_name}: {e}")
            # Return placeholder image on error
            return self._create_placeholder_map(candidate_name, width, height)
    
    def generate_comparison_map(
        self,
        candidates: List[Dict[str, Any]],
        width: int = 600,
        height: int = 400,
        zoom: int = 11,
    ) -> bytes:
        """
        Generate a map showing multiple candidates
        
        Args:
            candidates: List of candidates with 'name', 'lat', 'lng', 'score'
            width: Map width in pixels
            height: Map height in pixels
            zoom: Zoom level
        
        Returns:
            PNG image bytes of map
        """
        if not candidates:
            return self._create_placeholder_map("No locations", width, height)
        
        try:
            # Calculate center point
            lats = [c.get('lat') for c in candidates if 'lat' in c]
            lngs = [c.get('lng') for c in candidates if 'lng' in c]
            
            if not lats or not lngs:
                return self._create_placeholder_map("Invalid coordinates", width, height)
            
            center_lat = sum(lats) / len(lats)
            center_lng = sum(lngs) / len(lngs)
            
            # Build marker string for all candidates
            marker_strings = []
            colors = ['0x0066CC', '0xFF6B35', '0x2D9CDB', '0x28A745', '0xDC3545']
            
            for idx, candidate in enumerate(candidates[:5]):  # Limit to 5 markers
                color = colors[idx % len(colors)]
                label = chr(65 + idx)  # A, B, C, D, E
                marker_str = f"color:{color}|label:{label}|{candidate.get('lat')},{candidate.get('lng')}"
                marker_strings.append(marker_str)
            
            # Build map parameters
            params = {
                'center': f"{center_lat},{center_lng}",
                'zoom': zoom,
                'size': f"{width}x{height}",
                'style': self._get_map_style(),
                'scale': '1',
                'format': 'png',
            }
            
            # Add all markers
            for marker_str in marker_strings:
                params[f'markers'] = marker_str
                if len(marker_strings) > 1:
                    params['markers'] += f"&markers={marker_str}"
            
            if self.api_key:
                params['key'] = self.api_key
            
            # Request static map
            response = requests.get(self.STATIC_MAP_API, params=params, timeout=5)
            response.raise_for_status()
            
            # Add legend overlay
            map_image = Image.open(io.BytesIO(response.content))
            return self._add_comparison_legend(map_image, candidates)
            
        except Exception as e:
            logger.error(f"Failed to generate comparison map: {e}")
            return self._create_placeholder_map("Comparison Map", width, height)
    
    def _get_map_style(self) -> str:
        """Get custom map styling for professional appearance"""
        return "&style=feature:water|element:geometry|color:0xf0f0f0"
    
    def _add_map_title(self, image: Image.Image, title: str) -> bytes:
        """
        Add title text overlay to map image
        
        Args:
            image: PIL Image object
            title: Title text to overlay
        
        Returns:
            PNG bytes with title
        """
        try:
            # Create a new image with space for title
            width, height = image.size
            new_height = height + 40
            
            new_image = Image.new('RGB', (width, new_height), color='white')
            new_image.paste(image, (0, 40))
            
            # Draw title
            draw = ImageDraw.Draw(new_image)
            
            # Simple text rendering (fallback if font not available)
            text = title[:30]  # Truncate long titles
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            
            draw.text((text_x, 10), text, fill='#0066CC')
            
            # Convert to bytes
            output = io.BytesIO()
            new_image.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to add map title: {e}")
            # Return original image if overlay fails
            output = io.BytesIO()
            image.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
    
    def _add_comparison_legend(
        self,
        image: Image.Image,
        candidates: List[Dict[str, Any]],
    ) -> bytes:
        """
        Add legend overlay to comparison map
        
        Args:
            image: PIL Image object
            candidates: List of candidates for legend
        
        Returns:
            PNG bytes with legend
        """
        try:
            width, height = image.size
            legend_height = min(len(candidates) * 20 + 20, 150)
            
            # Create legend panel
            legend = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(legend)
            
            # Semi-transparent background for legend
            draw.rectangle(
                [(width - 180, 10), (width - 10, 10 + legend_height)],
                fill=(255, 255, 255, 220),
                outline=(0, 0, 0, 100),
            )
            
            # Draw legend items
            colors_hex = ['#0066CC', '#FF6B35', '#2D9CDB', '#28A745', '#DC3545']
            for idx, candidate in enumerate(candidates[:5]):
                y = 20 + idx * 20
                label = chr(65 + idx)
                
                # Color dot
                draw.ellipse(
                    [(width - 170, y), (width - 160, y + 10)],
                    fill=colors_hex[idx % len(colors_hex)],
                )
                
                # Label and score
                text = f"{label}: {candidate.get('name', 'Unknown')[:15]}"
                draw.text((width - 155, y - 2), text, fill='black')
            
            # Paste legend onto original image
            image.paste(legend, (0, 0), legend)
            
            # Convert to bytes
            output = io.BytesIO()
            image.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to add comparison legend: {e}")
            output = io.BytesIO()
            image.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
    
    def _create_placeholder_map(self, title: str, width: int = 400, height: int = 300) -> bytes:
        """
        Create a placeholder map when real map generation fails
        
        Args:
            title: Title for placeholder
            width: Width in pixels
            height: Height in pixels
        
        Returns:
            PNG bytes
        """
        try:
            image = Image.new('RGB', (width, height), color='#E8E8E8')
            draw = ImageDraw.Draw(image)
            
            # Draw border
            draw.rectangle([(0, 0), (width-1, height-1)], outline='#999999', width=2)
            
            # Draw placeholder text
            text = f"Map: {title}"
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            text_y = (height - 20) // 2
            
            draw.text((text_x, text_y), text, fill='#666666')
            draw.text((width//2 - 50, text_y + 25), "[Map unavailable]", fill='#999999')
            
            # Convert to bytes
            output = io.BytesIO()
            image.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create placeholder map: {e}")
            return b""  # Empty bytes on complete failure
