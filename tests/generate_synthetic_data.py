"""
Script to generate synthetic test cases for ITB RAG chatbot.

Generates ITB-specific test questions across multiple categories using LLM.
"""
import json
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


def generate_synthetic_test_cases():
    """Generate synthetic test cases for ITB RAG system.

    Returns:
        List of test case dictionaries with category, question, and expected_keywords.
    """
    # Use production LLM for test generation
    llm = ChatOpenAI(
        model="qwen/qwen3-235b-a22b",
        temperature=0,
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:8080"),
                "X-Title": os.getenv("APP_NAME", "ITB Chatbot"),
            },
        timeout=60,
    )

    # Prompts for different categories
    prompts = [
        "Generate 3 unique ITB admission questions in Indonesian. Mix formal and informal language.",
        "Generate 3 unique questions about ITB tuition fees and UKT payment in Indonesian.",
        "Generate 3 unique questions about academic programs and majors at ITB in Indonesian.",
        "Generate 3 unique questions about ITB campus facilities and policies in Indonesian.",
        "Generate 3 unique questions about ITB graduation requirements and honors in Indonesian.",
        "Generate 2 unique edge case questions about ITB (historical, very specific, or hypothetical scenarios).",
    ]

    test_cases = []

    for prompt in prompts:
        try:
            response = llm.invoke(prompt)
            questions = response.content.strip().split('\n')
            
            # Clean up questions (remove numbering, bullets)
            for q in questions:
                q = q.strip()
                # Remove common prefixes
                for prefix in ['1.', '2.', '3.', '4.', '-', '*', '•']:
                    if q.startswith(prefix):
                        q = q[len(prefix):].strip()
                
                # Skip empty questions
                if q and len(q) > 10:
                    # Determine category from prompt
                    if "admission" in prompt.lower() or "daftar" in prompt.lower():
                        category = "admissions"
                    elif "tuition" in prompt.lower() or "ukt" in prompt.lower() or "biaya" in prompt.lower():
                        category = "fees"
                    elif "academic" in prompt.lower() or "major" in prompt.lower() or "program" in prompt.lower():
                        category = "academics"
                    elif "facility" in prompt.lower() or "policy" in prompt.lower() or "campus" in prompt.lower():
                        category = "facilities"
                    elif "graduation" in prompt.lower() or "honors" in prompt.lower():
                        category = "graduation"
                    else:
                        category = "edge_cases"
                    
                    test_cases.append({
                        "category": category,
                        "question": q,
                        "expected_keywords": []  # Can be filled manually or via another prompt
                    })
        except Exception as e:
            print(f"Error generating questions for prompt '{prompt[:50]}...': {e}")
            continue

    # Deduplicate questions
    seen_questions = set()
    unique_cases = []
    for case in test_cases:
        q_lower = case["question"].lower()
        if q_lower not in seen_questions:
            seen_questions.add(q_lower)
            unique_cases.append(case)

    return unique_cases


if __name__ == "__main__":
    print("Generating synthetic test cases for ITB RAG chatbot...")
    
    test_cases = generate_synthetic_test_cases()
    
    output_file = "tests/data/synthetic_test_cases.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Generated {len(test_cases)} test cases")
    print(f"📁 Saved to {output_file}")
    
    # Print summary by category
    from collections import Counter
    categories = Counter([case["category"] for case in test_cases])
    print(f"\n📊 Breakdown by category:")
    for cat, count in categories.most_common():
        print(f"   {cat}: {count} questions")
