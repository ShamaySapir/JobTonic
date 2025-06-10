import os
import uuid
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, make_response
from asgiref.wsgi import WsgiToAsgi
import uvicorn
from src.helper import chat


load_dotenv()  # Load environment variables from .env file

port = int(os.getenv('PORT', 5000))  # Default to 5000 if PORT is not set

app = Flask(__name__)


# Create a web endpoint
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        message = data.get('message', '')
        history = json.loads(request.cookies.get('history', '[]'))

        chat_response = chat(message, history)
        response_data = {'message': chat_response}

        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            response_data['session_id'] = session_id

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": chat_response})
        response_data['history'] = history
        response_data['status'] = 'success'
        response = make_response(jsonify(response_data))

        response.set_cookie('session_id', session_id)
        response.set_cookie('history', json.dumps(history))

        return response

    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

# --- עטיפה ל-ASGI ---
app = WsgiToAsgi(app)

if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)