# Pro İklim Analiz Sistemi

Bu proje, Python ve Yapay Zeka teknolojileri kullanılarak geliştirilmiş, uçtan uca bir meteorolojik analiz ve tahmin sistemidir.

 **Canlı Demo:** [Uygulamayı Görüntüle](https://mucahidkeremhava.streamlit.app/)

##  Özellikler

* **Global Konumlandırma:** `Geopy` kütüphanesi ile dünyanın her yerindeki lokasyonların (Şehir, İlçe, Köy) koordinatlarını ve yerel saat dilimlerini otomatik algılar.
* **Canlı Veri Akışı:** `Open-Meteo API` entegrasyonu ile anlık hava durumu ve 7 günlük tahmin verilerini çeker.
* **Yapay Zeka Entegrasyonu:** `Google Gemini 2.0 Flash` modeli ile sayısal verileri işleyerek teknik mühendislik raporları oluşturur.
* **İnteraktif Görselleştirme:** `Plotly` ile dinamik, yakınlaştırılabilir sıcaklık, yağış ve rüzgar grafikleri sunar.
* **Veri İhracı:** Analiz edilen verilerin CSV (Excel) formatında indirilmesine olanak tanır.

##  Kullanılan Teknolojiler

* **Dil:** Python 3.10+
* **Arayüz:** Streamlit
* **Veri Bilimi:** Pandas, NumPy
* **Görselleştirme:** Plotly Graph Objects
* **API & AI:** Open-Meteo, Google Generative AI

##  Kurulum ve Çalıştırma (Local)

1.  Projeyi klonlayın:
    ```bash
    git clone [https://github.com/mucahidkerem/iklim-projesi-final.git](https://github.com/mucahidkerem/iklim-projesi-final.git)
    ```
2.  Gerekli kütüphaneleri yükleyin:
    ```bash
    pip install -r requirements.txt
    ```
3.  Uygulamayı başlatın:
    ```bash
    streamlit run app.py
    ```

---
👨‍💻 **Geliştirici:** Mücahid Kerem
