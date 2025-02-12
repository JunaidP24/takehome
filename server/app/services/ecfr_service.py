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
        """Get corrections for a specific title using the corrections API endpoint"""
        try:
            print(f"\nFetching corrections for title {title_number}")
            url = f"{self.BASE_URL}/admin/v1/corrections/title/{title_number}.json"
            response = self.session.get(url)
            
            if not response.ok:
                print(f"Failed to get corrections: {response.status_code}")
                return []
            
            data = response.json()
            corrections = data.get('ecfr_corrections', [])
            
            # Sort corrections by error_corrected date, most recent first
            corrections.sort(key=lambda x: x.get('error_corrected', ''), reverse=True)
            
            # Format corrections for frontend
            formatted_corrections = [
                {
                    'correction_date': correction.get('error_corrected'),
                    'correction_text': f"{correction.get('corrective_action')} - {correction.get('cfr_references', [{}])[0].get('cfr_reference', '')}",
                    'fr_citation': correction.get('fr_citation'),
                    'error_occurred': correction.get('error_occurred')
                }
                for correction in corrections
            ]
            
            print(f"Found {len(formatted_corrections)} corrections")
            return formatted_corrections

        except Exception as e:
            print(f"Error getting corrections: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return []

    def get_full_title_content(self, title_number):
        """Fetch and parse full content for a title"""
        try:
            # Get the latest date first
            titles_response = self.session.get(f"{self.BASE_URL}/versioner/v1/titles.json")
            if not titles_response.ok:
                print(f"Failed to get titles data: {titles_response.status_code}")
                return ''

            titles_data = titles_response.json()
            title_info = next(
                (t for t in titles_data.get('titles', []) if t.get('number') == int(title_number)),
                None
            )
            
            if not title_info or not title_info.get('latest_issue_date'):
                print("No title info or latest date found")
                return ''

            latest_date = title_info['latest_issue_date']
            
            # Try to get the full content
            content_url = f"{self.BASE_URL}/versioner/v1/structure/{latest_date}/title-{title_number}.json"
            print(f"Fetching content from: {content_url}")
            
            response = self.session.get(content_url)
            if not response.ok:
                print(f"Failed to get content: {response.status_code}")
                return ''

            structure_data = response.json()
            
            # Extract text from the structure recursively
            def extract_text(node):
                text = []
                # Get text from label and text fields
                if isinstance(node, dict):
                    text.extend([
                        str(node.get('label', '')),
                        str(node.get('label_description', '')),
                        str(node.get('text', '')),
                        str(node.get('content', ''))
                    ])
                    # Recursively process children
                    for child in node.get('children', []):
                        text.extend(extract_text(child))
                return text

            # Extract all text from the structure
            all_text = extract_text(structure_data)
            content = ' '.join(filter(None, all_text))  # Join non-empty strings
            
            # Clean up the text
            content = re.sub(r'\s+', ' ', content)  # Replace multiple spaces with single space
            content = re.sub(r'[^\w\s]', ' ', content)  # Remove punctuation
            content = content.strip()
            
            print(f"Extracted {len(content.split())} words from title {title_number}")
            return content

        except Exception as e:
            print(f"Error getting full content for title {title_number}: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return ''

    def get_agencies(self):
        """Fetch the list of agencies from the eCFR API"""
        try:
            response = self.session.get(f"{self.BASE_URL}/admin/v1/agencies.json")
            if not response.ok:
                print(f"Failed to get agencies: {response.status_code}")
                return {}

            data = response.json()
            agency_map = {}

            def process_agency(agency):
                # Add the main agency
                variations = [
                    agency['name'],
                    agency['short_name'],
                    agency['display_name']
                ]
                agency_map[agency['short_name']] = {
                    'variations': variations,
                    'name': agency['display_name'],
                    'cfr_references': agency.get('cfr_references', [])
                }
                
                # Process children recursively
                for child in agency.get('children', []):
                    process_agency(child)

            for agency in data.get('agencies', []):
                process_agency(agency)

            return agency_map

        except Exception as e:
            print(f"Error fetching agencies: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return {}

    def get_agency_word_counts(self, title_number, content):
        """Calculate word counts per agency mentioned in the content"""
        try:
            print(f"\nFetching agencies for title {title_number}")
            agencies = self.get_agencies()
            
            if not content or not agencies:
                print("No content or agencies found")
                return {}

            # Filter agencies to those that have references to this title
            relevant_agencies = {
                short_name: data
                for short_name, data in agencies.items()
                if any(ref.get('title') == int(title_number) 
                      for ref in data['cfr_references'])
            }
            print(f"Found {len(relevant_agencies)} agencies relevant to title {title_number}")

            # Initialize counters
            agency_mentions = {}    # Count of mentions per agency
            agency_word_counts = {} # Final word counts per agency
            
            # Split content into sections
            sections = re.split(r'(?=\n*§\s*\d+\.)', content)
            print(f"Processing {len(sections)} sections")
            
            total_words = len(re.findall(r'\b\w+\b', content))
            print(f"Total words in content: {total_words}")
            
            for i, section in enumerate(sections):
                if not section.strip():
                    continue
                    
                section_words = len(re.findall(r'\b\w+\b', section))
                if section_words == 0:
                    continue
                    
                print(f"\nProcessing section {i} with {section_words} words")
                
                # Count mentions for each agency in this section
                section_mentions = {}
                for short_name, data in relevant_agencies.items():
                    mention_count = 0
                    for variation in data['variations']:
                        if not variation:
                            continue
                        pattern = r'\b' + re.escape(variation) + r'\b'
                        matches = len(re.findall(pattern, section, re.IGNORECASE))
                        mention_count += matches
                    
                    if mention_count > 0:
                        section_mentions[short_name] = mention_count
                        agency_mentions[short_name] = agency_mentions.get(short_name, 0) + mention_count
                        print(f"Found {mention_count} mentions of {short_name} in section {i}")
                
                # Distribute section words based on mention counts
                if section_mentions:
                    total_section_mentions = sum(section_mentions.values())
                    for agency, mentions in section_mentions.items():
                        # Words attributed to this agency = (agency mentions / total mentions) * section words
                        agency_words = (mentions / total_section_mentions) * section_words
                        agency_word_counts[agency] = agency_word_counts.get(agency, 0) + agency_words

            # Calculate final counts
            final_counts = {}
            total_mentions = sum(agency_mentions.values())
            
            for agency, mentions in agency_mentions.items():
                if mentions > 0:
                    # Calculate word count proportional to mentions
                    word_count = agency_word_counts.get(agency, 0)
                    final_counts[agencies[agency]['name']] = round(word_count)
                    print(f"{agencies[agency]['name']}: {mentions} mentions, {round(word_count)} words")

            print("\nFinal agency word counts:")
            for agency, count in sorted(final_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"{agency}: {count} words ({agency_mentions.get(agency, 0)} mentions)")
            
            return final_counts

        except Exception as e:
            print(f"Error calculating agency word counts: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return {}

    def get_historical_changes(self, title_number, months=60):
        """Get historical changes in section and part counts"""
        try:
            print(f"\nGetting historical data for title {title_number}")
            
            # First get all available versions for this title
            versions_url = f"{self.BASE_URL}/versioner/v1/titles.json"
            versions_response = self.session.get(versions_url)
            if not versions_response.ok:
                print(f"Failed to get versions: {versions_response.status_code}")
                return {'dates': [], 'section_counts': [], 'part_counts': []}
            
            versions_data = versions_response.json()
            
            # Find the title's version history
            title_info = next(
                (t for t in versions_data.get('titles', []) 
                 if t.get('number') == int(title_number)),
                None
            )
            
            if not title_info:
                print(f"No version history found for title {title_number}")
                return {'dates': [], 'section_counts': [], 'part_counts': []}
            
            # Get the version dates from the title info
            cutoff_date = (datetime.now() - timedelta(days=30 * months)).strftime('%Y-%m-%d')
            relevant_dates = [
                date for date in title_info.get('version_dates', [])
                if date >= cutoff_date
            ]
            
            print(f"Found {len(relevant_dates)} versions since {cutoff_date}")
            
            historical_data = []
            for date in relevant_dates:
                try:
                    print(f"Fetching data for {date}")
                    url = f"{self.BASE_URL}/versioner/v1/structure/{date}/title-{title_number}.json"
                    response = self.session.get(url)
                    
                    if response.ok:
                        data = response.json()
                        section_count = self.count_sections(data)
                        part_count = self.count_parts(data)
                        print(f"Got data for {date}: {section_count} sections, {part_count} parts")
                        
                        historical_data.append({
                            'date': date,
                            'total_sections': section_count,
                            'total_parts': part_count
                        })
                    else:
                        print(f"Failed to get data for {date}: {response.status_code}")
                except Exception as e:
                    print(f"Error processing date {date}: {str(e)}")
                    continue

            # Sort by date
            historical_data.sort(key=lambda x: x['date'])
            
            # Extract the data into separate lists
            dates = [item['date'] for item in historical_data]
            section_counts = [item['total_sections'] for item in historical_data]
            part_counts = [item['total_parts'] for item in historical_data]

            print(f"Collected {len(historical_data)} historical data points")
            return {
                'dates': dates,
                'section_counts': section_counts,
                'part_counts': part_counts
            }

        except Exception as e:
            print(f"Error getting historical changes: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return {
                'dates': [],
                'section_counts': [],
                'part_counts': []
            }

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

            # Get full content and calculate metrics
            content = self.get_full_title_content(title_number)
            word_count = len(re.findall(r'\b\w+\b', content)) if content else 0
            total_sections = structure['total_sections'] or 1
            avg_words_per_section = round(word_count / total_sections, 2)
            
            # Calculate agency-specific word counts
            print("\nCalculating agency word counts...")
            agency_counts = self.get_agency_word_counts(title_number, content)
            print(f"Found word counts for {len(agency_counts)} agencies")
            
            print(f"Word count: {word_count}")
            print(f"Total sections: {total_sections}")
            print(f"Average words per section: {avg_words_per_section}")
            print(f"Agency word counts: {agency_counts}")

            versions = self.get_title_versions(title_number)
            corrections = self.get_title_corrections(title_number)
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
                    'average_words_per_section': avg_words_per_section,
                    'agency_word_counts': agency_counts
                },
                'historical_data': {
                    'section_counts': historical_data['section_counts'],
                    'dates': historical_data['dates'],
                    'part_counts': historical_data['part_counts']
                },
                'versions': {
                    'total_versions': len(historical_data['dates']),
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

    def count_sections(self, data):
        """Recursively count sections in the structure"""
        if not data:
            return 0
        
        count = 0
        # Check if current node is a section
        if data.get('type') == 'section':
            count += 1
        
        # Recursively count sections in children
        for child in data.get('children', []):
            count += self.count_sections(child)
        
        return count

    def count_parts(self, data):
        """Recursively count parts in the structure"""
        if not data:
            return 0
        
        count = 0
        # Check if current node is a part
        if data.get('type') == 'part':
            count += 1
        
        # Recursively count parts in children
        for child in data.get('children', []):
            count += self.count_parts(child)
        
        return count 