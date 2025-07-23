from dotenv import load_dotenv
import os
import uuid
import json
from flask import Flask, request, jsonify, make_response
from asgiref.wsgi import WsgiToAsgi
import uvicorn
from src.helper import chat, get_cookie_size_info


load_dotenv()  # Load environment variables from .env file
MAX_COOKIE_SIZE = int(os.getenv('MAX_COOKIE_SIZE', "4000"))  # Default to 4000 if not set
WARNING_THRESHOLD = float(os.getenv('WARNING_THRESHOLD', "0.8"))  # Default to 80% if not set

def create_app():
    flask_app = Flask(__name__)

    # --- REGISTER ROUTES ON flask_app ---

    @flask_app.route('/chat', methods=['POST'])
    def handle_chat():
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

            temp_history = history + [{"role": "user", "content": message}, 
                                      {"role": "assistant", "content": chat_response}]
            
            cookie_info = get_cookie_size_info(temp_history)

            if cookie_info['size'] > MAX_COOKIE_SIZE:
                return jsonify({
                    'error': 'Chat history is too long to continue',
                    'status': 'history_limit_reached',
                    'message': 'Your conversation history has reached the maximum size limit. Please choose an option:',
                    'options': [
                        {'action': 'clear_and_continue', 'label': 'Start new conversation'},
                        {'action': 'download_history', 'label': 'Download history and start new'},
                        {'action': 'summarize_and_continue', 'label': 'Summarize history and continue'}
                    ],
                    'cookie_info': cookie_info
                }), 413

            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": chat_response})

            cookie_info = get_cookie_size_info(temp_history)
            warning = None
            if cookie_info['percentage'] > WARNING_THRESHOLD * 100:
                warning = {
                    'message': f"Chat history is {cookie_info['percentage']:.1f}% full",
                    'suggestion': 'Consider starting a new conversation soon'
                }
            response_data['history'] = history
            response_data['status'] = 'success'
            response_data['cookie_info'] = cookie_info
            if warning:
                response_data['warning'] = warning
            response = make_response(jsonify(response_data))

            response.set_cookie('session_id', session_id)
            response.set_cookie('history', json.dumps(history))

            return response
        except ValueError as e:
            return jsonify({'error': str(e), 'status': 'bad_request'}), 400
        except Exception as e:
            flask_app.logger.exception("Unhandled error in /chat")
            return jsonify({'error': 'Internal server error', 'status': 'error'}), 500


    @flask_app.route('/clear-history', methods=['POST'])
    def clear_history():
        response = jsonify({
            'message': 'New conversation started',
            'status': 'success'
        })
        response.set_cookie('history', '[]', httponly=True, samesite='Lax')
        return response

    @flask_app.route('/download-history', methods=['GET'])
    def download_history():
        history = json.loads(request.cookies.get('history', '[]'))
        
        readable_history = []
        for msg in history:
            role = "You" if msg['role'] == 'user' else "Assistant"
            readable_history.append(f"{role}: {msg['content']}")
        
        return jsonify({
            'history': readable_history,
            'download_format': '\n\n'.join(readable_history),
            'status': 'success'
        })

    @flask_app.route('/summarize-history', methods=['POST'])
    def summarize_history():
        history = json.loads(request.cookies.get('history', '[]'))
        summary = chat("Please summarize our conversation briefly", history)
        new_history = [{"role": "system", "content": f"Previous conversation summary: {summary}"}]
        
        response = jsonify({
            'message': 'History summarized and conversation continues',
            'summary': summary,
            'status': 'success'
        })
        
        response.set_cookie('history', json.dumps(new_history), httponly=True, samesite='Lax')
        return response

    # Health check endpoint
    @flask_app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'healthy'})
    
    return flask_app


# יצירת האפליקציות
flask_app = create_app()
asgi_app   = WsgiToAsgi(flask_app)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    uvicorn.run("app:asgi_app", host="0.0.0.0", port=port, reload=True)