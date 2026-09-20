import re
from pathlib import Path
from typing import Optional

def verify_narrative_citations(
    narrative: dict,
    metrics: list[dict],
    alerts: list[dict],
    health: dict,
    stat_tests: dict
) -> dict:
    """
    Extract all numbers/percentages from narrative text and verify
    each against actual run data.
    """
    # Collect all verifiable values from run data
    known_values = set()
    
    # From metrics
    for m in metrics:
        if m.get('scalar_value') is not None:
            sv = m['scalar_value']
            # Add the raw value and common formatted versions
            known_values.add(round(sv, 4))
            known_values.add(round(sv, 2))
            known_values.add(round(sv * 100, 2))  # percentage form
            known_values.add(round(sv * 100, 1))
            known_values.add(int(round(sv * 100)))  # integer percentage
        if m.get('threshold_value') is not None:
            tv = m['threshold_value']
            known_values.add(round(tv, 4))
            known_values.add(round(tv, 2))
    
    # From health
    if health.get('score') is not None:
        known_values.add(health['score'])
        known_values.add(round(health['score'], 1))
    
    # From stat tests
    for t in (stat_tests.get('tests') or []):
        if t.get('statistic') is not None:
            known_values.add(round(t['statistic'], 4))
            known_values.add(round(t['statistic'], 2))
        if t.get('p_value') is not None:
            known_values.add(round(t['p_value'], 4))
    
    # From alerts
    for a in alerts:
        if a.get('observed_value') is not None:
            known_values.add(round(a['observed_value'], 4))
            known_values.add(round(a['observed_value'], 2))
        if a.get('threshold_value') is not None:
            known_values.add(round(a['threshold_value'], 4))
            known_values.add(round(a['threshold_value'], 2))
    
    # Also add finding counts
    known_values.add(len(metrics))
    known_values.add(len(alerts))
    
    # Extract all numbers from narrative text
    narrative_text = ' '.join([
        str(narrative.get('executive_summary', '')),
        str(narrative.get('technical_summary', '')),
        ' '.join(narrative.get('root_causes', [])),
        ' '.join(narrative.get('recommended_actions', []))
    ])
    
    # Regex to find numbers: integers, decimals, percentages
    number_pattern = r'(?<!\w)(\d+\.?\d*)\s*%?'
    found_numbers = re.findall(number_pattern, narrative_text)
    
    citations = []
    verified_count = 0
    unverified = []
    
    for num_str in found_numbers:
        try:
            num = float(num_str)
        except ValueError:
            continue
        
        # Skip trivially common numbers
        if num in (0, 1, 2, 3, 100):
            verified_count += 1
            continue
        
        # Check if number matches any known value
        is_verified = any(
            abs(num - kv) < 0.011 for kv in known_values if isinstance(kv, (int, float))
        )
        
        citation = {
            'value': num,
            'original_text': num_str,
            'verified': is_verified
        }
        citations.append(citation)
        
        if is_verified:
            verified_count += 1
        else:
            unverified.append(citation)
    
    total = len(citations)
    return {
        'verified': len(unverified) == 0,
        'total_citations': total,
        'verified_count': verified_count,
        'unverified_count': len(unverified),
        'verification_rate': round(verified_count / total * 100, 1) if total > 0 else 100.0,
        'unverified': unverified[:10],  # Limit to top 10
        'status': 'passed' if len(unverified) == 0 else ('warning' if len(unverified) <= 3 else 'failed')
    }
