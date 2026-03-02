import os
import logging
from flask import Flask

def create_app():
    # Caminhos absolutos para as pastas fora de /backend
    template_dir = os.path.abspath('frontend/templates')
    static_dir = os.path.abspath('frontend/static')

    app = Flask(__name__, 
                template_folder=template_dir, 
                static_folder=static_dir)

    # --- LOGS ---
    log_format = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    app.logger.handlers = [console_handler] 
    app.logger.setLevel(logging.INFO)

    # Registro de rotas
    from .routes import main
    app.register_blueprint(main)
    
    app.logger.info("🚀 Servidor pronto em http://127.0.0.1:5000")
    
    return app