import re
import io
from django.shortcuts import render
from django.http import JsonResponse
from pypdf import PdfReader

def home(request):
    return render(request, 'generator/index.html')

def process_text(request):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        difficulty = request.POST.get('difficulty', 'medium')
        
        # Check for file uploads if text content is missing
        if not content and 'file_upload' in request.FILES:
            uploaded_file = request.FILES['file_upload']
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            if file_ext == 'txt':
                content = uploaded_file.read().decode('utf-8')
            elif file_ext == 'pdf':
                try:
                    pdf_file = io.BytesIO(uploaded_file.read())
                    reader = PdfReader(pdf_file)
                    extracted_text = []
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            extracted_text.append(text)
                    content = "\n".join(extracted_text)
                except Exception:
                    return JsonResponse({'error': 'Failed to process PDF file.'}, status=400)

        if not content or len(content.strip()) < 10:
            return JsonResponse({'error': 'Please provide text content or upload a valid document.'}, status=400)
        
        # 1. Extractive Summary
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        summary = " ".join(sentences[:4])
        
        # 2. Difficulty Configuration Rules
        # Easy: Shorter common words. Medium: Core terms. Hard: Complex vocabulary.
        if difficulty == 'easy':
            word_pattern = r'\b[a-zA-Z]{4,5}\b'
            ignored_words = ['this', 'that', 'with', 'from', 'then', 'they', 'have', 'more']
        elif difficulty == 'hard':
            word_pattern = r'\b[a-zA-Z]{8,15}\b'
            ignored_words = ['structure', 'framework', 'different', 'important', 'something']
        else: # medium
            word_pattern = r'\b[a-zA-Z]{6,8}\b'
            ignored_words = ['system', 'process', 'concept', 'theory', 'method', 'around']

        quiz = []
        words_to_test = []
        
        for sentence in sentences:
            if len(quiz) >= 10:
                break
                
            clean_words = re.findall(word_pattern, sentence)
            for word in clean_words:
                if len(quiz) >= 10:
                    break
                if word.lower() in ignored_words or len(word) < 4:
                    continue
                if word.lower() not in [w.lower() for w in words_to_test]:
                    words_to_test.append(word)
                    
                    masked_sentence = re.sub(rf'\b{word}\b', '_______', sentence, flags=re.IGNORECASE)
                    
                    # Generate distracting options
                    fake_pool = ["Variable", "Function", "Property", "Instance", "Parameter", "Protocol", "Module", "Syntax"]
                    options = list(set([word] + [f for f in fake_pool if f.lower() != word.lower()][:3]))
                    
                    quiz.append({
                        'question': masked_sentence,
                        'correct': word,
                        'options': sorted(options),
                        'explanation': f"The correct answer is '{word}'. Full context: \"{sentence}\""
                    })

        # Fallback if text properties didn't match the filtering rules
        if not quiz:
            quiz.append({
                'question': "The backend architecture parsed this dataset dynamically using _______ logic.",
                'correct': "extractive",
                'options': ["extractive", "manual", "stagnant", "random"],
                'explanation': "The correct answer is 'extractive'. Full context: The system processes long documents directly on your device using native string parsing mechanics."
            })

        return JsonResponse({'summary': summary, 'quiz': quiz[:10]})
        
    return JsonResponse({'error': 'Invalid method'}, status=400)