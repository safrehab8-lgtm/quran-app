#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف تشغيل البرنامج
"""

import subprocess
import sys
import os

def check_python_version():
    """التحقق من إصدار Python"""
    if sys.version_info < (3, 6):
        print("❌ يتطلب البرنامج Python 3.6 أو أعلى")
        print(f"📌 إصدارك الحالي: {sys.version}")
        return False
    return True

def install_requirements():
    """تثبيت المتطلبات (إذا وجدت)"""
    if os.path.exists("requirements.txt"):
        print("📦 تثبيت المتطلبات...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ تم تثبيت المتطلبات بنجاح")
        except subprocess.CalledProcessError:
            print("⚠️  لا يمكن تثبيت المتطلبات، تأكد من وجود pip")
    else:
        print("✅ لا توجد متطلبات للتثبيت")

def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("📖 برنامج الاستئناف القرآني - تدريب الذاكرة")
    print("=" * 60)
    
    # التحقق من إصدار Python
    if not check_python_version():
        return
    
    # عرض التعليمات
    print("\n🎯 ميزات البرنامج:")
    print("  • اختبار عشوائي للآيات")
    print("  • دعم أجزاء متعددة من القرآن")
    print("  • نظام نقاط وتقييم")
    print("  • تتبع تقدم المستخدم")
    print("  • لوحة متصدرين")
    print("  • إدارة البيانات")
    
    print("\n📁 ملفات البرنامج:")
    print("  1. quran_data.json - قاعدة بيانات الآيات")
    print("  2. quran_recall.py - البرنامج الرئيسي")
    print("  3. user_progress.json - تقدم المستخدمين (سيتم إنشاؤه تلقائياً)")
    
    # عرض خيارات التشغيل
    print("\n🚀 خيارات التشغيل:")
    print("  1. تشغيل البرنامج")
    print("  2. إنشاء ملف بيانات مثال")
    print("  3. اختبار النظام")
    print("  4. خروج")
    
    while True:
        choice = input("\nاختر خياراً (1-4): ").strip()
        
        if choice == "1":
            print("\n▶️  تشغيل البرنامج...")
            from quran_recall import main as run_app
            run_app()
            break
        
        elif choice == "2":
            create_sample_data()
            break
        
        elif choice == "3":
            test_system()
            break
        
        elif choice == "4":
            print("👋 مع السلامة!")
            break
        
        else:
            print("❌ اختيار غير صالح")

def create_sample_data():
    """إنشاء ملف بيانات مثال"""
    sample_data = {
        "juz_amma": {
            "name": "جزء عم",
            "description": "الجزء الثلاثون من القرآن الكريم",
            "total_verses": 564,
            "surahs": [
                {
                    "id": 78,
                    "name": "سورة النبأ",
                    "verses": [
                        "عَمَّ يَتَسَاءَلُونَ",
                        "عَنِ النَّبَإِ الْعَظِيمِ",
                        "الَّذِي هُمْ فِيهِ مُخْتَلِفُونَ",
                        "كَلَّا سَيَعْلَمُونَ",
                        "ثُمَّ كَلَّا سَيَعْلَمُونَ"
                    ]
                }
            ]
        }
    }
    
    import json
    with open("quran_data.json", "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    print("✅ تم إنشاء ملف بيانات مثال 'quran_data.json'")
    print("\n📋 محتوى الملف:")
    print(json.dumps(sample_data, ensure_ascii=False, indent=2))

def test_system():
    """اختبار النظام"""
    print("\n🔍 اختبار النظام...")
    
    # التحقق من الملفات
    files = ["quran_recall.py"]
    missing_files = []
    
    for file in files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ الملفات الناقصة: {', '.join(missing_files)}")
        return
    
    print("✅ جميع الملفات المطلوبة موجودة")
    
    # اختبار استيراد المكتبات
    try:
        import json
        import random
        import re
        from datetime import datetime
        print("✅ المكتبات المطلوبة متاحة")
    except ImportError as e:
        print(f"❌ خطأ في استيراد المكتبات: {e}")
        return
    
    # اختبار تشغيل البرنامج
    print("\n🎯 يمكنك الآن تشغيل البرنامج بالخيار 1")

if __name__ == "__main__":
    main()