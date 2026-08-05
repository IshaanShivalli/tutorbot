from flask import Flask, request, jsonify

app = Flask(__name__)

# Load your AI model here (e.g., Llama 3 via Ollama, Hugging Face, or custom LMS logic)
def query_ai_model(prompt):
    # Placeholder for your AI model inference logic
    response_text = f"AI processed your LMS query: '{prompt}'"
    return response_text

@app.route('/ai-chat', methods=['POST'])
def ai_chat():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Invalid payload, 'prompt' required"}), 400
    
    user_prompt = data['prompt']
    print(f"Received prompt from ESP32 bridge: {user_prompt}")
    
    # Get response from your AI model
    ai_answer = query_ai_model(user_prompt)
    
    return jsonify({"response": ai_answer})

if __name__ == '__main__':
    # Run on port 5000, accessible locally by the ESP32
    app.run(host='0.0.0.0', port=5000)