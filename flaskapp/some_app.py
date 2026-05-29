import os
import numpy as np
import base64
from io import BytesIO
import requests
from flask import Flask, render_template, request, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import FloatField, StringField
from wtforms.validators import InputRequired, NumberRange
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Google reCAPTCHA ключи
app.config['RECAPTCHA_PUBLIC_KEY'] = '6Lfa3wEtAAAAADrGiLSa8fqiNYWafZOr0MjQzazY'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6Lfa3wEtAAAAAK-9GJ_hl-qNdP03SSOsflzR1I_s'

class ContrastForm(FlaskForm):
    """Форма с загрузкой изображения, контрастом и капчей"""
    image = FileField('Изображение', validators=[FileRequired()])
    contrast = FloatField(
        'Контраст (0.0 - минимум, 1.0 - оригинал, 2.0 - максимум)',
        default=1.0,
        validators=[InputRequired(), NumberRange(min=0.0, max=2.0)]
    )
    # Капча будет добавлена в шаблоне, так как WTForms не имеет встроенной reCAPTCHA

def verify_recaptcha(response_token):
    """Проверка капчи через Google API"""
    if not response_token:
        return False
    payload = {
        'secret': app.config['RECAPTCHA_PRIVATE_KEY'],
        'response': response_token
    }
    try:
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
        result = r.json()
        return result.get('success', False)
    except:
        return False

def adjust_contrast(image, contrast_level):
    img_array = np.array(image).astype(np.float32)
    img_normalized = img_array / 255.0
    adjusted = (img_normalized - 0.5) * contrast_level + 0.5
    adjusted = np.clip(adjusted, 0, 1)
    adjusted = (adjusted * 255).astype(np.uint8)
    return Image.fromarray(adjusted)

def compute_histogram(image):
    img_array = np.array(image)
    hist_r = np.histogram(img_array[:,:,0], bins=256, range=(0,256))[0]
    hist_g = np.histogram(img_array[:,:,1], bins=256, range=(0,256))[0]
    hist_b = np.histogram(img_array[:,:,2], bins=256, range=(0,256))[0]
    return hist_r, hist_g, hist_b

def plot_to_base64(hist_r, hist_g, hist_b, title):
    fig = plt.figure(figsize=(8, 4))
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
    plt.close(fig)
    buf.close()
    return img_base64

@app.route("/", methods=['GET', 'POST'])
def index():
    form = ContrastForm()
    original_image_path = None
    modified_image_path = None
    original_hist_base64 = None
    modified_hist_base64 = None
    contrast_level = 1.0
    captcha_error = None
    
    if request.method == 'POST':
        # Проверяем капчу
        recaptcha_token = request.form.get('g-recaptcha-response')
        if not verify_recaptcha(recaptcha_token):
            captcha_error = 'Пожалуйста, подтвердите, что вы не робот'
        elif form.validate_on_submit():
            contrast_level = form.contrast.data
            file = form.image.data
            
            if file and file.filename != '':
                original_path = os.path.join(app.config['UPLOAD_FOLDER'], 'original.png')
                file.save(original_path)
                original_image_path = url_for('static', filename='original.png')
                
                img = Image.open(original_path).convert('RGB')
                modified_img = adjust_contrast(img, contrast_level)
                
                modified_path = os.path.join(app.config['UPLOAD_FOLDER'], 'modified.png')
                modified_img.save(modified_path)
                modified_image_path = url_for('static', filename='modified.png')
                
                hist_r, hist_g, hist_b = compute_histogram(img)
                original_hist_base64 = plot_to_base64(hist_r, hist_g, hist_b, 'Original histogram')
                
                hist_r, hist_g, hist_b = compute_histogram(modified_img)
                modified_hist_base64 = plot_to_base64(hist_r, hist_g, hist_b, 'Modified histogram')
    
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

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
