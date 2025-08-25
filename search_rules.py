#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rules Search Utility - Fuzzy search through cycling rules in English and Russian
"""

import json
import re
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
import argparse
import sys


class RulesSearcher:
    def __init__(self, rules_file: str = "rules.json"):
        """Initialize the searcher with rules from JSON file"""
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
        except FileNotFoundError:
            print(f"Error: Rules file '{rules_file}' not found!")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in '{rules_file}'!")
            sys.exit(1)
    
    def fuzzy_search(self, query: str, threshold: float = 0.6, max_results: int = 10) -> List[Dict]:
        """
        Perform fuzzy search on both English and Russian text
        
        Args:
            query: Search query
            threshold: Similarity threshold (0.0 to 1.0)
            max_results: Maximum number of results to return
            
        Returns:
            List of matching rules with similarity scores
        """
        if not query.strip():
            return []
        
        # Check if query is just a number (rule number)
        if query.strip().isdigit():
            rule_number = int(query.strip())
            result = self.search_by_rule_number(rule_number)
            if result:
                return [{
                    'rule_number': result['rule_number'],
                    'text_eng': result['text_eng'],
                    'text_rus': result['text_rus'],
                    'similarity_score': 1.0,
                    'matched_language': 'Direct Rule Number',
                    'is_direct_rule': True
                }]
            else:
                return []
        
        query_lower = query.lower().strip()
        results = []
        
        for rule in self.rules:
            # Search in English text
            eng_score = self._calculate_similarity(query_lower, rule['text_eng'].lower())
            
            # Search in Russian text
            rus_score = self._calculate_similarity(query_lower, rule['text_rus'].lower())
            
            # Take the higher score
            best_score = max(eng_score, rus_score)
            
            if best_score >= threshold:
                results.append({
                    'rule_number': rule['rule_number'],
                    'text_eng': rule['text_eng'],
                    'text_rus': rule['text_rus'],
                    'similarity_score': best_score,
                    'matched_language': 'English' if eng_score > rus_score else 'Russian',
                    'is_direct_rule': False
                })
        
        # Sort by similarity score (highest first) and limit results
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:max_results]
    
    def _calculate_similarity(self, query: str, text: str) -> float:
        """Calculate similarity between query and text using multiple methods"""
        # Method 1: Exact phrase match (highest priority)
        if query in text:
            return 1.0
        
        # Method 2: Exact word sequence match (for multi-word queries)
        query_words = query.split()
        if len(query_words) > 1:
            # Check if words appear in sequence (with small gaps allowed)
            text_words = text.split()
            sequence_score = self._calculate_sequence_similarity(query_words, text_words)
            if sequence_score > 0.8:
                return sequence_score
        
        # Method 3: All words present (but not necessarily in sequence)
        if len(query_words) > 1:
            word_matches = sum(1 for word in query_words if word in text)
            if word_matches == len(query_words):  # All words found
                return 0.7
            elif word_matches > len(query_words) * 0.7:  # Most words found
                return 0.5 + (word_matches / len(query_words)) * 0.2
        
        # Method 4: Single word exact match
        if len(query_words) == 1:
            if query_words[0] in text:
                return 0.6
        
        # Method 5: Sequence matcher (good for general similarity)
        seq_score = SequenceMatcher(None, query, text).ratio()
        
        # Method 6: Word-based similarity
        text_words = set(text.split())
        
        if not query_words:
            return seq_score
        
        # Calculate word overlap
        intersection = set(query_words).intersection(text_words)
        union = set(query_words).union(text_words)
        
        if union:
            word_score = len(intersection) / len(union)
        else:
            word_score = 0.0
        
        # Method 7: Check for partial word matches (lower priority)
        partial_score = 0.0
        for query_word in query_words:
            for text_word in text_words:
                if query_word in text_word or text_word in query_word:
                    partial_score = max(partial_score, 0.3)
                    break
        
        # Combine scores with weights - prioritize exact matches
        final_score = (
            seq_score * 0.15 +
            word_score * 0.25 +
            partial_score * 0.25
        )
        
        return final_score
    
    def _calculate_sequence_similarity(self, query_words: List[str], text_words: List[str]) -> float:
        """Calculate similarity based on word sequence order"""
        if len(query_words) < 2:
            return 0.0
        
        # Find the best sequence match
        best_score = 0.0
        
        for i in range(len(text_words) - len(query_words) + 1):
            # Check if query words appear in sequence starting at position i
            matches = 0
            gaps = 0
            last_pos = i
            
            for j, query_word in enumerate(query_words):
                # Look for the word in a small window around the expected position
                window_start = max(0, last_pos - 2)
                window_end = min(len(text_words), last_pos + 3)
                
                found = False
                for k in range(window_start, window_end):
                    if text_words[k] == query_word:
                        matches += 1
                        gaps += max(0, k - last_pos - 1)  # Count gaps
                        last_pos = k + 1
                        found = True
                        break
                
                if not found:
                    break
            
            if matches == len(query_words):
                # Calculate score based on gaps and sequence
                gap_penalty = min(0.3, gaps * 0.1)
                score = 0.9 - gap_penalty
                best_score = max(best_score, score)
        
        return best_score
    
    def search_by_rule_number(self, rule_number: int) -> Dict:
        """Find a specific rule by number"""
        for rule in self.rules:
            if rule['rule_number'] == rule_number:
                return rule
        return None
    
    def search_by_keywords(self, keywords: List[str], threshold: float = 0.5) -> List[Dict]:
        """Search by multiple keywords (all must be present)"""
        if not keywords:
            return []
        
        results = []
        
        for rule in self.rules:
            eng_text = rule['text_eng'].lower()
            rus_text = rule['text_rus'].lower()
            
            # Check if all keywords are present in either language
            all_present = True
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in eng_text and keyword_lower not in rus_text:
                    all_present = False
                    break
            
            if all_present:
                # Calculate overall similarity score
                total_score = 0
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    eng_score = self._calculate_similarity(keyword_lower, eng_text)
                    rus_score = self._calculate_similarity(keyword_lower, rus_text)
                    total_score += max(eng_score, rus_score)
                
                avg_score = total_score / len(keywords)
                
                if avg_score >= threshold:
                    results.append({
                        'rule_number': rule['rule_number'],
                        'text_eng': rule['text_eng'],
                        'text_rus': rule['text_rus'],
                        'similarity_score': avg_score,
                        'matched_language': 'Both'
                    })
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results
    
    def display_results(self, results: List[Dict], show_scores: bool = False):
        """Display search results in a formatted way"""
        if not results:
            print("No results found.")
            return
        
        # Check if this is a direct rule number result
        if len(results) == 1 and results[0].get('is_direct_rule', False):
            result = results[0]
            print(f"\nRule #{result['rule_number']}:")
            print("=" * 80)
            print(f"English: {result['text_eng']}")
            print(f"Russian: {result['text_rus']}")
            return
        
        print(f"\nFound {len(results)} result(s):")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Rule #{result['rule_number']}")
            if show_scores:
                print(f"   Similarity: {result['similarity_score']:.3f}")
                print(f"   Language: {result['matched_language']}")
            
            print(f"   English: {result['text_eng']}")
            print(f"   Russian: {result['text_rus']}")
            print("-" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Fuzzy search through cycling rules in English and Russian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rules_search.py "bike"
  python rules_search.py "велосипед"
  python rules_search.py --rule 5
  python rules_search.py --keywords "helmet safety"
  python rules_search.py --threshold 0.8 "training"
        """
    )
    
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "--rule", "-r", type=int, 
        help="Search by specific rule number"
    )
    parser.add_argument(
        "--keywords", "-k", nargs="+", 
        help="Search by multiple keywords (all must be present)"
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=0.6,
        help="Similarity threshold (0.0 to 1.0, default: 0.6)"
    )
    parser.add_argument(
        "--max-results", "-m", type=int, default=10,
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--show-scores", "-s", action="store_true",
        help="Show similarity scores in results"
    )
    parser.add_argument(
        "--rules-file", "-f", default="rules.json",
        help="Path to rules JSON file (default: rules.json)"
    )
    
    args = parser.parse_args()
    
    # Initialize searcher
    searcher = RulesSearcher(args.rules_file)
    
    # Perform search based on arguments
    if args.rule:
        # Search by rule number
        result = searcher.search_by_rule_number(args.rule)
        if result:
            print(f"\nRule #{args.rule}:")
            print("=" * 80)
            print(f"English: {result['text_eng']}")
            print(f"Russian: {result['text_rus']}")
        else:
            print(f"Rule #{args.rule} not found.")
    
    elif args.keywords:
        # Search by keywords
        results = searcher.search_by_keywords(args.keywords, args.threshold)
        searcher.display_results(results, args.show_scores)
    
    elif args.query:
        # Fuzzy search
        results = searcher.fuzzy_search(args.query, args.threshold, args.max_results)
        searcher.display_results(results, args.show_scores)
    
    else:
        # Interactive mode
        print("Rules Search Utility - Interactive Mode")
        print("Type 'quit' or 'exit' to exit")
        print("Type 'help' for search tips")
        print("-" * 50)
        
        while True:
            try:
                query = input("\nSearch: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                elif query.lower() in ['help', 'h']:
                    print("\nSearch Tips:")
                    print("- Use simple words or phrases")
                    print("- Search works in both English and Russian")
                    print("- Try different thresholds: --threshold 0.8")
                    print("- Use --keywords for multiple word search")
                    print("- Use --rule for specific rule numbers")
                    continue
                elif not query:
                    continue
                
                results = searcher.fuzzy_search(query, args.threshold, args.max_results)
                searcher.display_results(results, args.show_scores)
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    main()
