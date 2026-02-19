import os
import json
import random
import threading
import urllib.request
from flask import Flask, render_template_string, jsonify, request

# ------------------ إعداد البيانات ------------------
DATA_FILE = "quran_data.json"
STATE_FILE = "last_ayah.json"
PROGRESS_FILE = "progress.json"

# ------------------ دوال تحميل البيانات (نفس الكود الأصلي) ------------------
def download_quran(progress_callback=None):
    url = "http://api.alquran.cloud/v1/quran/quran-uthmani"
    try:
        if progress_callback:
            progress_callback(5, "جاري الاتصال...")
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if progress_callback:
            progress_callback(30, "تم تحميل السور، جاري المعالجة...")

        surahs = []
        for s in data['data']['surahs']:
            surahs.append({
                'number': s['number'],
                'name': s['name'],
                'ayahs': [ayah['text'] for ayah in s['ayahs']]
            })

        juz_map = {}
        for s in data['data']['surahs']:
            for ayah in s['ayahs']:
                surah_num = s['number']
                ayah_num = ayah['numberInSurah']
                juz_num = ayah['juz']
                juz_map[(surah_num, ayah_num)] = juz_num

        if progress_callback:
            progress_callback(100, "اكتمل التحميل!")
        return {'surahs': surahs, 'juz_map': juz_map}
    except Exception as e:
        raise Exception(f"فشل التحميل: {str(e)}")

def load_local_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'surahs' in data and 'juz_map' in data:
                juz_map = {}
                for key_str, value in data['juz_map'].items():
                    try:
                        surah, ayah = map(int, key_str.strip('()').split(','))
                        juz_map[(surah, ayah)] = value
                    except:
                        continue
                data['juz_map'] = juz_map
                return data
        except:
            pass
    return None

def save_local_data(data):
    save_data = {
        'surahs': data['surahs'],
        'juz_map': {str(k): v for k, v in data['juz_map'].items()}
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

def load_last_ayah():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def save_last_ayah(surah, ayah, juz):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'surah': surah, 'ayah': ayah, 'juz': juz}, f)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('correct', 0), data.get('total', 0)
        except:
            pass
    return 0, 0

def save_progress(correct, total):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'correct': correct, 'total': total}, f)

class Api:
    def __init__(self):
        self.quran_data = None
        self.current_juz = 1
        self.ayahs_in_juz = []
        self.current_ayah = None
        self.answer_shown = False
        self.correct_count, self.total_count = load_progress()

    def _is_short_ayah(self, text):
        words = text.split()
        return len(words) <= 3

    def _get_next_ayah_info(self):
        if not self.ayahs_in_juz or not self.current_ayah:
            return None
        try:
            idx = self.ayahs_in_juz.index(self.current_ayah)
        except ValueError:
            return None
        if idx < len(self.ayahs_in_juz) - 1:
            return self.ayahs_in_juz[idx + 1]
        return None

    def record_correct(self):
        self.correct_count += 1
        self.total_count += 1
        save_progress(self.correct_count, self.total_count)
        return self.get_progress()

    def record_wrong(self):
        self.total_count += 1
        save_progress(self.correct_count, self.total_count)
        return self.get_progress()

    def get_progress(self):
        if self.total_count == 0:
            return {'percent': 0, 'correct': 0, 'total': 0}
        percent = int((self.correct_count / self.total_count) * 100)
        return {'percent': percent, 'correct': self.correct_count, 'total': self.total_count}

    def load_local(self):
        self.quran_data = load_local_data()
        if self.quran_data:
            last = load_last_ayah()
            if last:
                self.current_juz = last.get('juz', 1)
                self.build_juz_ayahs(self.current_juz)
                for ayah in self.ayahs_in_juz:
                    if ayah[0] == last['surah'] and ayah[1] == last['ayah']:
                        self.current_ayah = ayah
                        break
                if not self.current_ayah and self.ayahs_in_juz:
                    self.current_ayah = self.ayahs_in_juz[0]
            else:
                self.build_juz_ayahs(1)
                if self.ayahs_in_juz:
                    self.current_ayah = self.ayahs_in_juz[0]
            return {'success': True, 'message': 'أهلاً بك في مراجعة القرآن الكريم', 'progress': self.get_progress()}
        else:
            return {'success': False, 'message': 'الرجاء تحميل القرآن أولاً'}

    def build_juz_ayahs(self, juz_number):
        if not self.quran_data:
            return
        self.ayahs_in_juz = []
        juz_map = self.quran_data['juz_map']
        surahs = self.quran_data['surahs']
        for surah in surahs:
            s_num = surah['number']
            for a_num, text in enumerate(surah['ayahs'], start=1):
                if juz_map.get((s_num, a_num)) == juz_number:
                    self.ayahs_in_juz.append((s_num, a_num, text))
        self.current_juz = juz_number

    def set_juz(self, juz):
        juz = int(juz)
        self.build_juz_ayahs(juz)
        if self.ayahs_in_juz:
            self.current_ayah = self.ayahs_in_juz[0]
            self.answer_shown = False
        return {'success': True, 'message': f'تم اختيار الجزء {juz}'}

    def download(self):
        try:
            data = download_quran()
            save_local_data(data)
            self.quran_data = data
            self.build_juz_ayahs(1)
            if self.ayahs_in_juz:
                self.current_ayah = self.ayahs_in_juz[0]
            return {'success': True, 'message': 'تم تحميل القرآن بنجاح', 'progress': self.get_progress()}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_current(self):
        if not self.current_ayah:
            return {'error': 'لا توجد آية'}
        surah_num, ayah_num, full_text = self.current_ayah
        surah_name = self.quran_data['surahs'][surah_num-1]['name']
        if not self.answer_shown:
            words = full_text.split()
            partial = ' '.join(words[:3]) + ' ...'
            return {
                'partial': partial,
                'full': full_text,
                'surah': surah_name,
                'ayah': ayah_num,
                'answer_shown': False
            }
        else:
            return {
                'partial': full_text,
                'full': full_text,
                'surah': surah_name,
                'ayah': ayah_num,
                'answer_shown': True
            }

    def show_answer(self):
        if not self.current_ayah:
            return {'error': 'لا توجد آية'}
        surah_num, ayah_num, full_text = self.current_ayah
        surah_name = self.quran_data['surahs'][surah_num-1]['name']
        if self._is_short_ayah(full_text):
            next_ayah = self._get_next_ayah_info()
            if next_ayah:
                s_num, a_num, text = next_ayah
                s_name = self.quran_data['surahs'][s_num-1]['name']
                self.answer_shown = True
                return {
                    'full': text,
                    'surah': s_name,
                    'ayah': a_num,
                    'note': 'الآية التالية (لأن الآية الأصلية قصيرة)'
                }
        self.answer_shown = True
        return {
            'full': full_text,
            'surah': surah_name,
            'ayah': ayah_num,
            'note': ''
        }

    def next_ayah(self):
        if not self.ayahs_in_juz or not self.current_ayah:
            return {'error': 'لا توجد آية تالية'}
        try:
            idx = self.ayahs_in_juz.index(self.current_ayah)
        except ValueError:
            idx = -1
        if idx < len(self.ayahs_in_juz) - 1:
            self.current_ayah = self.ayahs_in_juz[idx + 1]
            self.answer_shown = False
            surah_num, ayah_num, _ = self.current_ayah
            save_last_ayah(surah_num, ayah_num, self.current_juz)
            return self.get_current()
        else:
            return {'error': 'هذه آخر آية في الجزء'}

    def random_ayah(self):
        if not self.ayahs_in_juz:
            return {'error': 'لا توجد آيات'}
        self.current_ayah = random.choice(self.ayahs_in_juz)
        self.answer_shown = False
        surah_num, ayah_num, _ = self.current_ayah
        save_last_ayah(surah_num, ayah_num, self.current_juz)
        return self.get_current()

# ------------------ تهيئة Flask ------------------
app = Flask(__name__)
api = Api()  # إنشاء كائن Api واحد للتطبيق بأكمله

# ------------------ صفحة HTML الرئيسية ------------------
HTML_PAGE = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مراجعة القرآن الكريم</title>
    <style>
        /* نفس الـ CSS الأصلي */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            transition: background-color 0.3s, color 0.3s;
        }
        body {
            font-family: 'Amiri', 'Traditional Arabic', serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            position: relative;
        }
        /* شاشة البداية */
        .splash {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: #0a2f44;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            transition: opacity 0.5s;
        }
        .splash-content {
            text-align: center;
            color: #ffd966;
        }
        .splash-content img {
            width: 120px;
            height: 120px;
            margin-bottom: 20px;
        }
        .splash-content h1 {
            font-size: 48px;
            margin-bottom: 20px;
            text-shadow: 3px 3px 0 #000;
        }
        .splash-content p {
            font-size: 24px;
            color: white;
        }
        /* الوضع الشمسي (افتراضي) */
        body.light-mode {
            background: #ffffff;
        }
        body.light-mode .container {
            background: #f8f9fa;
            border: 2px solid #2ecc71;
            box-shadow: 0 25px 50px -12px #00000040;
        }
        body.light-mode h1 {
            color: #2c3e50;
            text-shadow: 2px 2px 0 #ecf0f1;
        }
        body.light-mode .juz-box {
            background: #ecf0f1;
            border: 1px solid #bdc3c7;
        }
        body.light-mode .juz-box label {
            color: #2c3e50;
        }
        body.light-mode .juz-box select {
            background: white;
            color: #2c3e50;
        }
        body.light-mode .progress-text {
            color: #2c3e50;
        }
        body.light-mode .ayah-card {
            background: white;
            border: 2px solid #27ae60;
            box-shadow: 0 10px 20px -5px #00000030;
        }
        body.light-mode .ayah-text {
            color: #2c3e50;
        }
        body.light-mode .surah-info {
            color: #7f8c8d;
            border-top: 1px dashed #bdc3c7;
        }
        body.light-mode .next-label {
            color: #2c3e50;
        }
        body.light-mode .status {
            color: #27ae60;
        }
        body.light-mode .footer {
            color: #7f8c8d;
        }
        body.light-mode .btn-green {
            background: #27ae60;
            color: white;
        }
        body.light-mode .btn-blue {
            background: #2980b9;
            color: white;
        }
        body.light-mode .btn-gold {
            background: #f39c12;
            color: white;
        }
        body.light-mode .btn-purple {
            background: #9b59b6;
            color: white;
        }
        body.light-mode .btn-red {
            background: #e74c3c;
            color: white;
        }
        body.light-mode .btn-gray {
            background: #95a5a6;
            color: white;
        }

        /* الوضع الليلي */
        body.dark-mode {
            background: #1a1a2e;
        }
        body.dark-mode .container {
            background: #16213e;
            border: 2px solid #0f3460;
            box-shadow: 0 25px 50px -12px #00000080;
        }
        body.dark-mode h1 {
            color: #e94560;
            text-shadow: 2px 2px 0 #0f3460;
        }
        body.dark-mode .juz-box {
            background: #0f3460;
            border: 1px solid #e94560;
        }
        body.dark-mode .juz-box label {
            color: #f1f1f1;
        }
        body.dark-mode .juz-box select {
            background: #16213e;
            color: #f1f1f1;
            border: 1px solid #e94560;
        }
        body.dark-mode .progress-text {
            color: #f1f1f1;
        }
        body.dark-mode .progress-bar {
            background-color: #e94560;
        }
        body.dark-mode .ayah-card {
            background: #0f3460;
            border: 2px solid #e94560;
            box-shadow: 0 10px 20px -5px #00000080;
        }
        body.dark-mode .ayah-text {
            color: #f1f1f1;
        }
        body.dark-mode .surah-info {
            color: #a5a5a5;
            border-top: 1px dashed #e94560;
        }
        body.dark-mode .next-label {
            color: #e94560;
        }
        body.dark-mode .status {
            color: #e94560;
        }
        body.dark-mode .footer {
            color: #a5a5a5;
        }
        body.dark-mode .btn-green {
            background: #0f3460;
            color: #e94560;
            border: 1px solid #e94560;
        }
        body.dark-mode .btn-blue {
            background: #0f3460;
            color: #e94560;
            border: 1px solid #e94560;
        }
        body.dark-mode .btn-gold {
            background: #0f3460;
            color: #e94560;
            border: 1px solid #e94560;
        }
        body.dark-mode .btn-purple {
            background: #0f3460;
            color: #e94560;
            border: 1px solid #e94560;
        }
        body.dark-mode .btn-red {
            background: #0f3460;
            color: #e94560;
            border: 1px solid #e94560;
        }
        body.dark-mode .btn-gray {
            background: #0f3460;
            color: #e94560;
            border: 1px solid #e94560;
        }

        .container {
            width: 100%;
            max-width: 750px;
            border-radius: 40px;
            padding: 30px;
        }
        h1 {
            font-size: 48px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            font-family: 'Amiri', serif;
        }
        .quran-icon {
            width: 60px;
            height: 60px;
        }
        .mode-toggle {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 10px;
        }
        .mode-btn {
            background: none;
            border: none;
            font-size: 30px;
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 50px;
            transition: 0.3s;
        }
        .mode-btn:hover {
            transform: scale(1.1);
        }
        .progress-bar-container {
            background-color: #ecf0f1;
            border-radius: 50px;
            height: 20px;
            width: 100%;
            margin: 10px 0 20px;
            overflow: hidden;
        }
        .progress-bar {
            background-color: #27ae60;
            height: 100%;
            width: 0%;
            transition: width 0.3s;
        }
        .progress-text {
            text-align: center;
            font-size: 18px;
            margin-bottom: 10px;
            font-family: 'Amiri', serif;
        }
        .juz-box {
            border-radius: 60px;
            padding: 15px 25px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 25px;
        }
        .juz-box label {
            font-size: 22px;
            font-weight: bold;
            font-family: 'Amiri', serif;
        }
        .juz-box select {
            border: none;
            padding: 12px 25px;
            border-radius: 40px;
            font-size: 20px;
            font-family: 'Amiri', serif;
            font-weight: bold;
            outline: none;
            cursor: pointer;
            box-shadow: 0 5px 10px #00000020;
        }
        .btn-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 25px 0;
            flex-wrap: wrap;
        }
        .btn {
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
            box-shadow: 0 5px 0 #bdc3c7;
            font-family: 'Amiri', serif;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn:active {
            transform: translateY(4px);
            box-shadow: 0 2px 0 #bdc3c7;
        }
        .ayah-card {
            border-radius: 30px;
            padding: 20px;
            margin: 15px 0;
        }
        .ayah-text {
            font-family: 'Amiri', serif;
            font-size: 30px;
            line-height: 2;
            text-align: center;
            margin-bottom: 10px;
            word-spacing: 4px;
        }
        .surah-info {
            font-size: 18px;
            text-align: center;
            font-style: italic;
            padding-top: 10px;
            font-family: 'Amiri', serif;
        }
        .next-label {
            font-size: 22px;
            text-align: center;
            margin: 15px 0 5px;
            font-weight: bold;
            font-family: 'Amiri', serif;
        }
        .status {
            text-align: center;
            font-size: 18px;
            margin: 15px 0 5px;
            min-height: 30px;
            font-family: 'Amiri', serif;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            font-size: 18px;
            font-family: 'Amiri', serif;
        }
        .feedback-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 20px;
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap" rel="stylesheet">
</head>
<body class="light-mode">
    <!-- شاشة البداية -->
    <div class="splash" id="splash">
        <div class="splash-content">
            <img src="https://cdn-icons-png.flaticon.com/512/3039/3039285.png" alt="مصحف">
            <h1>مراجعة القرآن الكريم</h1>
            <p>مع المصحف الشريف</p>
        </div>
    </div>

    <div class="container">
        <!-- زر تبديل الوضع -->
        <div class="mode-toggle">
            <button class="mode-btn" id="modeToggle">🌙</button>
        </div>

        <h1>
            <img src="https://cdn-icons-png.flaticon.com/512/3039/3039285.png" class="quran-icon" alt="مصحف">
            مراجعة القرآن الكريم
        </h1>

        <!-- شريط التقدم والنسبة المئوية -->
        <div class="progress-text" id="progressText">0% (0/0)</div>
        <div class="progress-bar-container">
            <div class="progress-bar" id="progressBar" style="width: 0%;"></div>
        </div>

        <!-- اختيار الجزء -->
        <div class="juz-box">
            <label>📖 اختر الجزء:</label>
            <select id="juzSelect">
                <option value="1">الجزء ١</option>
                <option value="2">الجزء ٢</option>
                <option value="3">الجزء ٣</option>
                <option value="4">الجزء ٤</option>
                <option value="5">الجزء ٥</option>
                <option value="6">الجزء ٦</option>
                <option value="7">الجزء ٧</option>
                <option value="8">الجزء ٨</option>
                <option value="9">الجزء ٩</option>
                <option value="10">الجزء ١٠</option>
                <option value="11">الجزء ١١</option>
                <option value="12">الجزء ١٢</option>
                <option value="13">الجزء ١٣</option>
                <option value="14">الجزء ١٤</option>
                <option value="15">الجزء ١٥</option>
                <option value="16">الجزء ١٦</option>
                <option value="17">الجزء ١٧</option>
                <option value="18">الجزء ١٨</option>
                <option value="19">الجزء ١٩</option>
                <option value="20">الجزء ٢٠</option>
                <option value="21">الجزء ٢١</option>
                <option value="22">الجزء ٢٢</option>
                <option value="23">الجزء ٢٣</option>
                <option value="24">الجزء ٢٤</option>
                <option value="25">الجزء ٢٥</option>
                <option value="26">الجزء ٢٦</option>
                <option value="27">الجزء ٢٧</option>
                <option value="28">الجزء ٢٨</option>
                <option value="29">الجزء ٢٩</option>
                <option value="30">الجزء ٣٠</option>
            </select>
        </div>

        <!-- الأزرار العلوية -->
        <div class="btn-group">
            <button class="btn btn-green" id="downloadBtn">📥 تحميل القرآن</button>
            <button class="btn btn-blue" id="newAyahBtn">🌟 آية عشوائية</button>
        </div>

        <!-- الآية الحالية -->
        <div class="ayah-card">
            <div class="ayah-text" id="ayahText">اضغط على "تحميل القرآن" أولاً</div>
            <div class="surah-info" id="surahInfo"></div>
        </div>

        <!-- عنوان الإجابة -->
        <div class="next-label">الإجابة:</div>

        <!-- الإجابة -->
        <div class="ayah-card" style="background: #f0fff0; border-color: #2ecc71;">
            <div class="ayah-text" id="answerText">(سيظهر هنا نص الإجابة)</div>
            <div class="surah-info" id="answerInfo"></div>
        </div>

        <!-- أزرار التقييم (صح/غلط) -->
        <div class="feedback-buttons">
            <button class="btn btn-green" id="correctBtn" disabled>✅ صح</button>
            <button class="btn btn-red" id="wrongBtn" disabled>❌ غلط</button>
        </div>

        <!-- أزرار التحكم -->
        <div class="btn-group">
            <button class="btn btn-gold" id="showAnswerBtn">👁 إظهار الإجابة</button>
            <button class="btn btn-purple" id="nextBtn">⏪ التالي (في الجزء)</button>
        </div>

        <!-- رسالة الحالة -->
        <div class="status" id="status"></div>

        <!-- تذييل -->
        <div class="footer">
            { إنا نحن نزلنا الذكر وإنا له لحافظون }
        </div>
    </div>

    <script>
        // إخفاء شاشة البداية بعد 2 ثانية
        setTimeout(function() {
            document.getElementById('splash').style.opacity = '0';
            setTimeout(function() {
                document.getElementById('splash').style.display = 'none';
            }, 500);
        }, 2000);

        // تبديل الوضع
        document.getElementById('modeToggle').addEventListener('click', function() {
            const body = document.body;
            if (body.classList.contains('light-mode')) {
                body.classList.remove('light-mode');
                body.classList.add('dark-mode');
                this.innerText = '☀️';
            } else {
                body.classList.remove('dark-mode');
                body.classList.add('light-mode');
                this.innerText = '🌙';
            }
        });

        // دالة لاستدعاء API
        async function callApi(method, data = {}) {
            const response = await fetch('/api/' + method, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await response.json();
        }

        // تحديث شريط التقدم
        function updateProgress(progress) {
            document.getElementById('progressBar').style.width = progress.percent + '%';
            document.getElementById('progressText').innerText = progress.percent + '% (' + progress.correct + '/' + progress.total + ')';
        }

        // تمكين/تعطيل أزرار التقييم
        function enableFeedback(enable) {
            document.getElementById('correctBtn').disabled = !enable;
            document.getElementById('wrongBtn').disabled = !enable;
        }

        // تحديث عرض الآية الحالية
        async function updateDisplay() {
            const result = await callApi('get_current');
            if (!result.error) {
                document.getElementById('ayahText').innerText = result.partial;
                document.getElementById('surahInfo').innerText = `سورة ${result.surah} - آية ${result.ayah}`;
                if (result.answer_shown) {
                    document.getElementById('answerText').innerText = result.full;
                    document.getElementById('answerInfo').innerText = `سورة ${result.surah} - آية ${result.ayah}`;
                    enableFeedback(true);
                } else {
                    document.getElementById('answerText').innerText = '(سيظهر هنا نص الإجابة)';
                    document.getElementById('answerInfo').innerText = '';
                    enableFeedback(false);
                }
            }
        }

        document.getElementById('juzSelect').addEventListener('change', async function() {
            const result = await callApi('set_juz', { juz: this.value });
            document.getElementById('status').innerText = result.message;
            updateDisplay();
            enableFeedback(false);
        });

        document.getElementById('downloadBtn').addEventListener('click', async function() {
            document.getElementById('status').innerText = 'جاري تحميل القرآن...';
            const result = await callApi('download');
            if (result.success) {
                document.getElementById('status').innerText = result.message;
                updateProgress(result.progress);
                updateDisplay();
            } else {
                document.getElementById('status').innerText = 'خطأ: ' + result.message;
            }
        });

        document.getElementById('newAyahBtn').addEventListener('click', async function() {
            const result = await callApi('random_ayah');
            if (result.error) {
                document.getElementById('status').innerText = result.error;
            } else {
                document.getElementById('ayahText').innerText = result.partial;
                document.getElementById('surahInfo').innerText = `سورة ${result.surah} - آية ${result.ayah}`;
                document.getElementById('answerText').innerText = '(سيظهر هنا نص الإجابة)';
                document.getElementById('answerInfo').innerText = '';
                document.getElementById('status').innerText = '';
                enableFeedback(false);
            }
        });

        document.getElementById('showAnswerBtn').addEventListener('click', async function() {
            const result = await callApi('show_answer');
            if (result.error) {
                document.getElementById('status').innerText = result.error;
            } else {
                document.getElementById('answerText').innerText = result.full;
                document.getElementById('answerInfo').innerText = `سورة ${result.surah} - آية ${result.ayah}`;
                document.getElementById('status').innerText = result.note || '';
                enableFeedback(true);
            }
        });

        // أزرار التقييم
        document.getElementById('correctBtn').addEventListener('click', async function() {
            const progress = await callApi('record_correct');
            updateProgress(progress);
            document.getElementById('status').innerText = 'تم تسجيل الإجابة الصحيحة ✓';
            enableFeedback(false);
        });

        document.getElementById('wrongBtn').addEventListener('click', async function() {
            const progress = await callApi('record_wrong');
            updateProgress(progress);
            document.getElementById('status').innerText = 'تم تسجيل الإجابة الخاطئة ✗';
            enableFeedback(false);
        });

        document.getElementById('nextBtn').addEventListener('click', async function() {
            const result = await callApi('next_ayah');
            if (result.error) {
                document.getElementById('status').innerText = result.error;
            } else {
                document.getElementById('ayahText').innerText = result.partial;
                document.getElementById('surahInfo').innerText = `سورة ${result.surah} - آية ${result.ayah}`;
                document.getElementById('answerText').innerText = '(سيظهر هنا نص الإجابة)';
                document.getElementById('answerInfo').innerText = '';
                document.getElementById('status').innerText = '';
                enableFeedback(false);
            }
        });

        window.onload = async function() {
            const result = await callApi('load_local');
            document.getElementById('status').innerText = result.message;
            if (result.success) {
                if (result.progress) updateProgress(result.progress);
                updateDisplay();
            }
        };
    </script>
</body>
</html>
'''

# ------------------ مسارات API ------------------
@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/api/<method>', methods=['POST'])
def api_call(method):
    data = request.get_json() or {}
    if method == 'get_current':
        return jsonify(api.get_current())
    elif method == 'random_ayah':
        return jsonify(api.random_ayah())
    elif method == 'set_juz':
        return jsonify(api.set_juz(data.get('juz', 1)))
    elif method == 'download':
        return jsonify(api.download())
    elif method == 'show_answer':
        return jsonify(api.show_answer())
    elif method == 'next_ayah':
        return jsonify(api.next_ayah())
    elif method == 'record_correct':
        return jsonify(api.record_correct())
    elif method == 'record_wrong':
        return jsonify(api.record_wrong())
    elif method == 'load_local':
        return jsonify(api.load_local())
    else:
        return jsonify({'error': 'دالة غير معروفة'})

# ------------------ تشغيل التطبيق ------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
