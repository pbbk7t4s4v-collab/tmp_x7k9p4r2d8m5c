#!/usr/bin/env python3
"""
Search API using Exa with configuration from config.json
"""

import json
import os
import argparse
from exa_py import Exa


class SearchAPI:
    """Search API class that handles configuration and search operations"""
    
    def __init__(self, config_path="config.json"):
        """Initialize the SearchAPI with configuration from JSON file"""
        self.config_path = config_path
        self.config = self._load_config()
        self.exa = Exa(self.config['exa_api_key'])
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            # Get the directory of the current script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file_path = os.path.join(script_dir, self.config_path)
            
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if not config.get('exa_api_key') or config['exa_api_key'] == "your_exa_api_key_here":
                raise ValueError("Please set your EXA_API_KEY in config.json")
            
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in configuration file {self.config_path}")
    
    def search_and_contents(self, query, search_type=None, include_text=None, max_results=None):
        """
        Search for content using Exa API
        
        Args:
            query (str): Search query
            search_type (str, optional): Type of search ('auto', 'neural', 'keyword')
            include_text (bool, optional): Whether to include text content
            max_results (int, optional): Maximum number of results
        
        Returns:
            Search results from Exa API
        """
        # Use config defaults if parameters not specified
        search_settings = self.config.get('search_settings', {})
        
        if search_type is None:
            search_type = search_settings.get('default_type', 'auto')
        
        if include_text is None:
            include_text = search_settings.get('include_text', True)
        
        if max_results is None:
            max_results = search_settings.get('max_results', 10)
        
        try:
            result = self.exa.search_and_contents(
                query,
                type=search_type,
                text=include_text,
                num_results=max_results
            )
            return result
        except Exception as e:
            print(f"Error during search: {e}")
            return None
    
    def search(self, query, search_type=None, max_results=None):
        """
        Simple search without content (only URLs and titles)
        
        Args:
            query (str): Search query
            search_type (str, optional): Type of search ('auto', 'neural', 'keyword')
            max_results (int, optional): Maximum number of results
        
        Returns:
            Search results from Exa API
        """
        search_settings = self.config.get('search_settings', {})
        
        if search_type is None:
            search_type = search_settings.get('default_type', 'auto')
        
        if max_results is None:
            max_results = search_settings.get('max_results', 10)
        
        try:
            result = self.exa.search(
                query,
                type=search_type,
                num_results=max_results
            )
            return result
        except Exception as e:
            print(f"Error during search: {e}")
            return None


def main():
    """Main function that handles command line arguments and performs search"""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Search API using Exa - search for any topic",
        epilog="Example: python search_api.py \"KNN是什么\""
    )
    parser.add_argument(
        "query", 
        nargs="?",  # Makes the query optional
        default="An article about the state of AGI",
        help="Search query (default: 'An article about the state of AGI')"
    )
    parser.add_argument(
        "--type", 
        choices=["auto", "neural", "keyword"],
        default=None,
        help="Search type (default: uses config setting)"
    )
    parser.add_argument(
        "--max-results", 
        type=int,
        default=None,
        help="Maximum number of results (default: uses config setting)"
    )
    parser.add_argument(
        "--no-text", 
        action="store_true",
        help="Only get URLs and titles, no text content"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        # Initialize the search API
        api = SearchAPI()
        
        # Display search query
        print(f"Searching for: '{args.query}'")
        print("-" * 50)
        
        # Perform search based on arguments
        if args.no_text:
            result = api.search(
                args.query, 
                search_type=args.type, 
                max_results=args.max_results
            )
        else:
            result = api.search_and_contents(
                args.query, 
                search_type=args.type, 
                include_text=True,
                max_results=args.max_results
            )
        
        if result:
            print("\n=== Search Results ===")
            print(result)
        else:
            print("No results or error occurred")
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease make sure to:")
        print("1. Install required packages: pip install exa_py")
        print("2. Set your EXA_API_KEY in config.json")


if __name__ == "__main__":
    main()