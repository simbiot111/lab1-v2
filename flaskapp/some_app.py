import os
import numpy as np
import base64
from io import BytesIO
import requests
from flask import Flask, render_template, request, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import FloatField
from wtforms.validators import InputRequired, NumberRange
from PIL import Image
import matplotlib
matplotlib.use('Agg')  # Без GUI — для работы в Flask
import matplotlib.pyplot as plt

# ====================================
# Конфигурация приложения
# ====================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Ключи Google reCAPTCHA (v2)
app.config['RECAPTCHA_PUBLIC_KEY'] = '6Lfa3wEtAAAAADrGiLSa8fqiNYWafZOr0MjQzazY'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6Lfa3wEtAAAAAK-9GJ_hl-qNdP03SSOsflzR1I_s'

# ====================================
# Форма (Flask-WTF)
# ====================================

class ContrastForm(FlaskForm):
    image = FileField('Изображение', validators=[FileRequired()])
    contrast = FloatField(
        'Контраст (0.0–2.0)',
        default=1.0,
        validators=[InputRequired(), NumberRange(min=0.0, max=2.0)]
    )

# ====================================
# Проверка капчи
# ====================================

def verify_recaptcha(response_token):
    """Отправляет токен в Google API, возвращает True если капча пройдена"""
    if not response_token:
        return False
    payload = {
        'secret': app.config['RECAPTCHA_PRIVATE_KEY'],
        'response': response_token
    }
    try:
        result = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload).json()
        return result.get('success', False)
    except:
        return False

# ====================================
# Обработка изображений
# ====================================

def adjust_contrast(image, contrast_level):
    """Изменяет контраст: (пиксель - 0.5) * contrast + 0.5"""
    img_array = np.array(image).astype(np.float32) / 255.0
    adjusted = (img_array - 0.5) * contrast_level + 0.5
    adjusted = np.clip(adjusted, 0, 1)
    adjusted = np.round(adjusted * 255).astype(np.uint8)
    return Image.fromarray(adjusted)

def compute_histogram(image):
    """Возвращает гистограммы для каналов R, G, B"""
    img_array = np.array(image)
    hist_r = np.histogram(img_array[:,:,0], bins=256, range=(0,256))[0]
    hist_g = np.histogram(img_array[:,:,1], bins=256, range=(0,256))[0]
    hist_b = np.histogram(img_array[:,:,2], bins=256, range=(0,256))[0]
    return hist_r, hist_g, hist_b

def plot_to_base64(hist_r, hist_g, hist_b, title):
    """Строит график гистограммы и возвращает base64-строку для вставки в HTML"""
    plt.figure(figsize=(8, 4))
    plt.plot(hist_r, color='red', label='Red')
    plt.plot(hist_g, color='green', label='Green')
    plt.plot(hist_b, color='blue', label='Blue')
    plt.title(title)
    plt.xlabel('Pixel intensity')
    plt.ylabel('Frequency')
    plt.legend()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    buf.close()
    return img_base64

# ====================================
# Маршруты
# ====================================

@app.route("/", methods=['GET', 'POST'])
def index():
    form = ContrastForm()
    original_image_path = modified_image_path = None
    original_hist_base64 = modified_hist_base64 = None
    contrast_level = 1.0
    captcha_error = None
    
    if request.method == 'POST':
        recaptcha_token = request.form.get('g-recaptcha-response')
        
        if not verify_recaptcha(recaptcha_token):
            captcha_error = 'Пожалуйста, подтвердите, что вы не робот'
        elif form.validate_on_submit():
            contrast_level = form.contrast.data
            file = form.image.data
            
            if file:
                # Сохраняем оригинал
                original_path = os.path.join(app.config['UPLOAD_FOLDER'], 'original.png')
                file.save(original_path)
                original_image_path = url_for('static', filename='original.png')
                
                # Обрабатываем контраст
                img = Image.open(original_path).convert('RGB')
                modified_img = adjust_contrast(img, contrast_level)
                
                modified_path = os.path.join(app.config['UPLOAD_FOLDER'], 'modified.png')
                modified_img.save(modified_path)
                modified_image_path = url_for('static', filename='modified.png')
                
                # Гистограммы
                hist_r, hist_g, hist_b = compute_histogram(img)
                original_hist_base64 = plot_to_base64(hist_r, hist_g, hist_b, 'Original')
                
                hist_r, hist_g, hist_b = compute_histogram(modified_img)
                modified_hist_base64 = plot_to_base64(hist_r, hist_g, hist_b, 'Modified')
    
    return render_template(
        'index.html',
        form=form,
        original_image=original_image_path,
        modified_image=modified_image_path,
        original_hist=original_hist_base64,
        modified_hist=modified_hist_base64,
        contrast=contrast_level,
        captcha_error=captcha_error,
        recaptcha_site_key=app.config['RECAPTCHA_PUBLIC_KEY']
    )

# ====================================
# Запуск
# ====================================

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
