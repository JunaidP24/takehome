import requests
from datetime import datetime, date, timedelta
import json
import traceback
from collections import defaultdict
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

class ECFRService:
    BASE_URL = "https://www.ecfr.gov/api"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, application/xml'
        })

    def get_all_titles(self):
        """Fetch all available titles from eCFR"""
        try:
            response = self.session.get(f"{self.BASE_URL}/versioner/v1/titles.json")
            response.raise_for_status()
            print(response.json())
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching titles: {str(e)}")
            raise Exception(f"Failed to fetch titles: {str(e)}")

    def parse_structure(self, structure_data):
        """Parse the hierarchical structure data"""
        if not structure_data:
            return {
                'name': '',
                'parts': [],
                'total_parts': 0,
                'total_sections': 0
            }

        def count_sections(node):
            """Recursively count non-reserved sections"""
            if node.get('type') == 'section' and not node.get('reserved', False):
                return 1
            return sum(count_sections(child) for child in node.get('children', []))

        def get_parts(node):
            """Recursively get parts"""
            if node.get('type') == 'part' and not node.get('reserved', False):
                return [{
                    'number': node.get('identifier'),
                    'name': node.get('label_description'),
                    'sections': count_sections(node)
                }]
            parts = []
            for child in node.get('children', []):
                parts.extend(get_parts(child))
            return parts

        # Get title information
        name = structure_data.get('label_description', '')
        parts = get_parts(structure_data)
        total_parts = len([p for p in parts if p['sections'] > 0])  # Only count parts with sections
        total_sections = sum(p['sections'] for p in parts)

        return {
            'name': name,
            'parts': parts,
            'total_parts': total_parts,
            'total_sections': total_sections
        }

    def get_title_structure(self, title_number, date_str=None):
        """Fetch title structure for a specific date"""
        try:
            # First get the titles data to find latest date
            titles_response = self.session.get(f"{self.BASE_URL}/versioner/v1/titles.json")
            if not titles_response.ok:
                print(f"Failed to get titles data: {titles_response.status_code}")
                return None

            titles_data = titles_response.json()
            title_info = next(
                (t for t in titles_data.get('titles', []) if t.get('number') == int(title_number)),
                None
            )
            
            if not title_info:
                print(f"Title {title_number} not found in titles data")
                return None

            # Use provided date or latest issue date
            use_date = date_str or title_info.get('latest_issue_date')
            if not use_date:
                print("No valid date found")
                return None

            print(f"Fetching structure for date: {use_date}")
            url = f"{self.BASE_URL}/versioner/v1/structure/{use_date}/title-{title_number}.json"
            response = self.session.get(url)
            
            if response.ok:
                data = response.json()
                return self.parse_structure(data)
            else:
                print(f"Failed to get structure: {response.text}")
                return None

        except Exception as e:
            print(f"Error in get_title_structure: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return None

    def get_title_versions(self, title_number):
        """Get all versions of sections in a title"""
        try:
            response = self.session.get(f"{self.BASE_URL}/versioner/v1/versions/title-{title_number}.json")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching title versions: {str(e)}")
            raise Exception(f"Failed to fetch title versions: {str(e)}")

    def get_title_corrections(self, title_number):
        """Get corrections for a specific title"""
        try:
            response = self.session.get(f"{self.BASE_URL}/admin/v1/corrections/title/{title_number}.json")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching title corrections: {str(e)}")
            raise Exception(f"Failed to fetch title corrections: {str(e)}")

    def get_full_title_content(self, title_number):
        """Fetch and parse full XML content for a title"""
        try:
            # Get the latest issue date
            titles_response = self.session.get(f"{self.BASE_URL}/versioner/v1/titles.json")
            if not titles_response.ok:
                return ''

            titles_data = titles_response.json()
            title_info = next(
                (t for t in titles_data.get('titles', []) if t.get('number') == int(title_number)),
                None
            )
            
            if not title_info or not title_info.get('latest_issue_date'):
                return ''

            latest_date = title_info['latest_issue_date']
            
            # Try different content endpoints
            endpoints = [
                f"{self.BASE_URL}/versioner/v1/full/{latest_date}/title-{title_number}/title-{title_number}.xml",
                f"{self.BASE_URL}/versioner/v1/full/{latest_date}/title-{title_number}.xml",
                f"{self.BASE_URL}/versioner/v1/structure/{latest_date}/title-{title_number}.json"
            ]

            content_text = ''
            for endpoint in endpoints:
                try:
                    print(f"Trying endpoint: {endpoint}")
                    response = self.session.get(endpoint)
                    if response.ok:
                        if endpoint.endswith('.xml'):
                            # Parse XML content
                            soup = BeautifulSoup(response.content, 'xml')
                            # Extract text from all content tags
                            content_tags = soup.find_all(['content', 'title', 'subject', 'text'])
                            content_text = ' '.join(tag.get_text() for tag in content_tags)
                            break
                        elif endpoint.endswith('.json'):
                            # Parse JSON structure
                            data = response.json()
                            content_text = self.extract_text_from_structure(data)
                            break
                except Exception as e:
                    print(f"Error with endpoint {endpoint}: {str(e)}")
                    continue

            # Clean up the text
            content_text = re.sub(r'\s+', ' ', content_text)  # Replace multiple spaces
            content_text = re.sub(r'[^\w\s]', ' ', content_text)  # Remove punctuation
            return content_text.strip()

        except Exception as e:
            print(f"Error fetching full title content: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return ''

    def extract_text_from_structure(self, data):
        """Recursively extract text from structure data"""
        text_content = []
        
        def extract_text(node):
            if isinstance(node, dict):
                # Extract text from relevant fields
                text_fields = ['label_description', 'subject', 'text', 'title', 'content']
                for field in text_fields:
                    if field in node:
                        text_content.append(str(node[field]))
                
                # Recursively process children
                if 'children' in node:
                    for child in node['children']:
                        extract_text(child)
            elif isinstance(node, list):
                for item in node:
                    extract_text(item)

        extract_text(data)
        return ' '.join(text_content)

    def get_agency_word_counts(self, title_number, content):
        """Analyze word count by agency"""
        try:
            # Get structure to identify agencies/parts
            structure = self.get_title_structure(title_number)
            if not structure or 'parts' not in structure:
                return {}

            agency_counts = defaultdict(int)
            
            # Count words for each part
            for part in structure['parts']:
                part_name = part.get('name', '')
                if part_name:
                    # Use regex to find words in the content that appear near the part name
                    context_window = 1000  # Characters to look before/after part name
                    part_pattern = re.escape(part_name)
                    matches = re.finditer(part_pattern, content)
                    
                    for match in matches:
                        start = max(0, match.start() - context_window)
                        end = min(len(content), match.end() + context_window)
                        context = content[start:end]
                        words = len(re.findall(r'\w+', context))
                        agency_counts[part_name] += words

            return dict(agency_counts)

        except Exception as e:
            print(f"Error analyzing agency word counts: {str(e)}")
            return {}

    def get_historical_changes(self, title_number):
        """Get historical changes for a title over the past year"""
        try:
            # Get the latest issue date from titles endpoint
            titles_response = self.session.get(f"{self.BASE_URL}/versioner/v1/titles.json")
            if not titles_response.ok:
                return []

            titles_data = titles_response.json()
            title_info = next(
                (t for t in titles_data.get('titles', []) if t.get('number') == int(title_number)),
                None
            )

            if not title_info or not title_info.get('latest_issue_date'):
                return []

            # Start from latest date and work backwards
            latest_date = datetime.strptime(title_info['latest_issue_date'], '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=365)
            changes = []
            
            current_date = latest_date
            while current_date >= start_date:
                date_str = current_date.strftime("%Y-%m-%d")
                try:
                    response = self.session.get(
                        f"{self.BASE_URL}/versioner/v1/structure/{date_str}/title-{title_number}.json"
                    )
                    if response.ok:
                        structure_data = response.json()
                        # Parse the structure data
                        parsed_structure = self.parse_structure(structure_data)
                        changes.append({
                            'date': date_str,
                            'total_parts': parsed_structure['total_parts'],
                            'total_sections': parsed_structure['total_sections']
                        })
                        print(f"Got data for {date_str}: {parsed_structure['total_sections']} sections")
                except Exception as e:
                    print(f"Error fetching historical data for {date_str}: {str(e)}")
                
                # Move back 30 days
                current_date -= timedelta(days=30)
            
            # Sort changes by date
            changes.sort(key=lambda x: x['date'])
            return changes

        except Exception as e:
            print(f"Error fetching historical changes: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return []

    def get_latest_update_date(self, title_number):
        """Get the actual latest update date for a title"""
        try:
            # Get titles data
            titles_response = self.session.get(f"{self.BASE_URL}/versioner/v1/titles.json")
            if not titles_response.ok:
                return None

            titles_data = titles_response.json()
            title_info = next(
                (t for t in titles_data.get('titles', []) if t.get('number') == int(title_number)),
                None
            )

            if title_info:
                # Use latest_issue_date as the primary source of truth
                return title_info.get('latest_issue_date')

            return None

        except Exception as e:
            print(f"Error getting latest update date: {str(e)}")
            return None

    def analyze_title(self, title_number):
        """Enhanced analysis including word count and historical data"""
        try:
            print(f"\nStarting analysis for title {title_number}")
            
            # Get latest update date first
            latest_date = self.get_latest_update_date(title_number)
            if not latest_date:
                print("Could not determine latest update date")
            
            # Get basic title data
            structure = self.get_title_structure(title_number)
            if not structure:
                print("Failed to get title structure")
                raise Exception("Could not fetch title structure")

            versions = self.get_title_versions(title_number)
            corrections = self.get_title_corrections(title_number)
            content = self.get_full_title_content(title_number)
            word_count = len(re.findall(r'\w+', content)) if content else 0
            agency_counts = self.get_agency_word_counts(title_number, content)
            historical_data = self.get_historical_changes(title_number)

            analysis = {
                'title_number': title_number,
                'name': structure['name'],
                'structure': {
                    'total_parts': structure['total_parts'],
                    'total_sections': structure['total_sections'],
                    'parts': structure['parts']
                },
                'metrics': {
                    'word_count': word_count,
                    'average_words_per_section': round(word_count / (structure['total_sections'] or 1), 2),
                    'agency_word_counts': agency_counts
                },
                'historical_data': {
                    'section_counts': [change['total_sections'] for change in historical_data],
                    'dates': [change['date'] for change in historical_data],
                    'part_counts': [change['total_parts'] for change in historical_data]
                },
                'versions': {
                    'total_versions': len(historical_data),
                    'latest_update': latest_date
                },
                'corrections': {
                    'total_corrections': len(corrections) if isinstance(corrections, list) else 0,
                    'recent_corrections': [
                        {
                            'date': c.get('correction_date'),
                            'description': c.get('correction_text')
                        }
                        for c in (corrections if isinstance(corrections, list) else [])[:5]
                    ]
                }
            }
            
            print(f"Analysis complete for title {title_number}")
            print(f"Latest update date: {latest_date}")
            return analysis
            
        except Exception as e:
            print(f"Error analyzing title {title_number}: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return {
                'title_number': title_number,
                'name': f'Title {title_number}',
                'structure': {
                    'total_parts': 0,
                    'total_sections': 0,
                    'parts': []
                },
                'metrics': {
                    'word_count': 0,
                    'average_words_per_section': 0,
                    'agency_word_counts': {}
                },
                'historical_data': {
                    'section_counts': [],
                    'dates': [],
                    'part_counts': []
                },
                'versions': {
                    'total_versions': 0,
                    'latest_update': None
                },
                'corrections': {
                    'total_corrections': 0,
                    'recent_corrections': []
                },
                'error': str(e)
            } 