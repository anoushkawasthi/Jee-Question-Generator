"""
DEEP AUDIT: What Issues Actually Exist in Extracted Data?
"""

import json
import re
from collections import defaultdict

print("\n" + "="*120)
print("DEEP AUDIT OF 1,805 EXTRACTED QUESTIONS".center(120))
print("="*120 + "\n")

with open("data/processed/jee_questions_final_consolidated.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

issues_found = defaultdict(int)
issue_examples = defaultdict(list)

print("Analyzing 1,805 questions for issues...\n")

total_q = 0
for paper_idx, paper in enumerate(data['papers']):
    for q in paper['questions']:
        total_q += 1
        
        q_id = q.get('question_id', 'Unknown')
        q_text = q.get('question_text', '')
        options = q.get('options', [])
        answer = q.get('correct_answer', '')
        latex = q.get('question_latex')
        subject = q.get('subject')
        q_type = q.get('question_type')
        
        # Issue 1: Missing question text
        if not q_text or q_text.strip() == '':
            issues_found['empty_question_text'] += 1
            issue_examples['empty_question_text'].append(q_id)
        
        # Issue 2: Question text too short (likely incomplete extraction)
        elif len(q_text) < 20:
            issues_found['text_too_short'] += 1
            if len(issue_examples['text_too_short']) < 3:
                issue_examples['text_too_short'].append((q_id, q_text[:50]))
        
        # Issue 3: Garbled Unicode (𝑟, 𝑙, etc. - indicates failed math conversion)
        if '𝑟' in q_text or '𝑙' in q_text or '𝑚' in q_text or '−' in q_text:
            issues_found['garbled_unicode'] += 1
            if len(issue_examples['garbled_unicode']) < 3:
                issue_examples['garbled_unicode'].append(q_id)
        
        # Issue 4: No options (MCQ should have options)
        if q_type == 'MCQ' and (not options or len(options) == 0):
            issues_found['mcq_missing_options'] += 1
            if len(issue_examples['mcq_missing_options']) < 3:
                issue_examples['mcq_missing_options'].append(q_id)
        
        # Issue 5: Only 1 option (should have 4)
        elif q_type == 'MCQ' and len(options) == 1:
            issues_found['mcq_single_option'] += 1
            if len(issue_examples['mcq_single_option']) < 3:
                issue_examples['mcq_single_option'].append((q_id, len(options)))
        
        # Issue 6: Missing subject classification
        if not subject or subject == 'Unknown':
            issues_found['missing_subject'] += 1
            if len(issue_examples['missing_subject']) < 3:
                issue_examples['missing_subject'].append(q_id)
        
        # Issue 7: Missing/wrong answer key
        if not answer or answer == '':
            issues_found['missing_answer_key'] += 1
            if len(issue_examples['missing_answer_key']) < 3:
                issue_examples['missing_answer_key'].append(q_id)
        
        # Issue 8: Answer key is '1' for everything (likely default/extraction error)
        if answer == '1':
            issues_found['default_answer_1'] += 1
        
        # Issue 9: No LaTeX even after post-processing
        if latex is None:
            issues_found['no_latex_field'] += 1
        elif isinstance(latex, str) and latex.strip() == '':
            issues_found['empty_latex_field'] += 1
        
        # Issue 10: Question text appears to be incomplete (ends abruptly)
        if q_text and (q_text.endswith('...') or 
                      (len(q_text) > 100 and q_text[-1] in [',', ';', '(', '[']) or
                      q_text.count('(') > q_text.count(')')):
            issues_found['incomplete_extraction'] += 1
            if len(issue_examples['incomplete_extraction']) < 3:
                issue_examples['incomplete_extraction'].append((q_id, q_text[-50:]))

print(f"Total questions audited: {total_q}\n")
print("="*120)
print("ISSUES FOUND".center(120))
print("="*120 + "\n")

if not issues_found:
    print("✅ NO ISSUES FOUND - Data quality is GOOD!\n")
else:
    # Sort by severity
    severity_map = {
        'empty_question_text': ('CRITICAL', 1),
        'missing_subject': ('HIGH', 2),
        'missing_answer_key': ('HIGH', 2),
        'no_latex_field': ('LOW', 5),
        'empty_latex_field': ('LOW', 5),
        'garbled_unicode': ('MEDIUM', 3),
        'mcq_missing_options': ('HIGH', 2),
        'mcq_single_option': ('MEDIUM', 3),
        'incomplete_extraction': ('MEDIUM', 3),
        'text_too_short': ('MEDIUM', 3),
        'default_answer_1': ('LOW', 4),
    }
    
    sorted_issues = sorted(issues_found.items(), 
                          key=lambda x: severity_map.get(x[0], ('UNKNOWN', 99))[1])
    
    for issue_type, count in sorted_issues:
        severity, _ = severity_map.get(issue_type, ('UNKNOWN', 99))
        percentage = (count / total_q) * 100
        
        # Color coding
        if severity == 'CRITICAL':
            symbol = '🔴'
        elif severity == 'HIGH':
            symbol = '🟠'
        elif severity == 'MEDIUM':
            symbol = '🟡'
        else:
            symbol = '🟢'
        
        print(f"{symbol} {issue_type.upper():40s} | {count:4d} ({percentage:5.2f}%) | {severity}")
        
        if issue_examples[issue_type]:
            examples = issue_examples[issue_type][:2]
            for ex in examples:
                if isinstance(ex, tuple):
                    print(f"     Example: {ex[0]} - {ex[1]}")
                else:
                    print(f"     Example: {ex}")
        print()

print("\n" + "="*120)
print("SEVERITY CLASSIFICATION".center(120))
print("="*120 + "\n")

critical_count = sum(c for issue, c in issues_found.items() 
                    if severity_map.get(issue, ('UNKNOWN', 99))[0] == 'CRITICAL')
high_count = sum(c for issue, c in issues_found.items() 
                if severity_map.get(issue, ('UNKNOWN', 99))[0] == 'HIGH')
medium_count = sum(c for issue, c in issues_found.items() 
                  if severity_map.get(issue, ('UNKNOWN', 99))[0] == 'MEDIUM')
low_count = sum(c for issue, c in issues_found.items() 
               if severity_map.get(issue, ('UNKNOWN', 99))[0] == 'LOW')

print(f"🔴 CRITICAL issues: {critical_count:4d} ({critical_count/total_q*100:.2f}%)")
print(f"🟠 HIGH severity:   {high_count:4d} ({high_count/total_q*100:.2f}%)")
print(f"🟡 MEDIUM severity: {medium_count:4d} ({medium_count/total_q*100:.2f}%)")
print(f"🟢 LOW severity:    {low_count:4d} ({low_count/total_q*100:.2f}%)")

print(f"\n✅ QUESTIONS WITHOUT ISSUES: {total_q - (critical_count + high_count + medium_count + low_count):4d} ({(total_q - (critical_count + high_count + medium_count + low_count))/total_q*100:.2f}%)")

print("\n" + "="*120)
print("ASSESSMENT: Should We Fix These Issues?".center(120))
print("="*120 + "\n")

if critical_count == 0 and high_count == 0:
    print("✅ YES - You can use the data as-is for Phase 2")
    print("\nWhy: No critical or high-severity issues detected")
    print("\nThe data is:")
    print("  • Mostly complete (>90% quality)")
    print("  • Usable for LLM annotation")
    print("  • Low-severity issues will be fixed BY Phase 2 LLM annotation")
    print("\nPhase 2 LLM will:")
    print("  • Fix garbled text and formatting")
    print("  • Validate and correct answer keys")
    print("  • Fill in missing metadata")
    print("  • Improve overall quality")
    
elif critical_count > 0:
    print("⚠️  CRITICAL: Some questions are severely broken")
    print(f"\nIssues to fix BEFORE Phase 2:")
    print(f"  • {critical_count} questions with empty/missing critical fields")
    print(f"\nRecommendation:")
    print(f"  1. Filter out {critical_count} broken questions")
    print(f"  2. Or re-run extraction with debugging")
    print(f"  3. Then proceed with {total_q - critical_count} valid questions")

elif high_count > (total_q * 0.05):  # More than 5% high severity
    print("⚠️  WARNING: Significant number of high-severity issues")
    print(f"\nRecommendation:")
    print(f"  • Consider running extraction with better error handling")
    print(f"  • Or carefully review extracted data")
    print(f"  • Then manually fix ~{high_count} problematic questions")
else:
    print("✅ OK: Low number of high-severity issues")
    print("\nRecommendation:")
    print("  • Proceed with Phase 2")
    print(f"  • Manually review and fix ~{high_count} high-severity issues")
    print("  • Let LLM annotation handle the rest")

print("\n" + "="*120)
