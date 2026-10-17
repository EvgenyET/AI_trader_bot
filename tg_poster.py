# tg_poster.py

import io
import asyncio
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt, QBuffer, QIODevice
from PyQt5.QtGui import QFont
import config
import telegram
from telegram.constants import ParseMode

class _TelegramPreviewDialog(QDialog):
    def __init__(self, image_pixmap, text, parent=None):
        super().__init__(parent)
        self.image_pixmap = image_pixmap
        self.text = text
        self.setWindowTitle("Предпросмотр и отправка поста")
        self.setMinimumSize(600, 850)
        self.setStyleSheet("""...""") # Стили
        self.layout = QVBoxLayout(self)
        self.image_label = QLabel()
        scaled_image = self.image_pixmap.scaledToWidth(580, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_image)
        self.layout.addWidget(self.image_label)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.text)
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)
        self.post_button = QPushButton("Запостить в Telegram")
        self.post_button.setFont(QFont('Arial', 12, QFont.Bold))
        self.post_button.setStyleSheet("background-color: #2a9d8f; color: white; padding: 12px;")
        self.post_button.clicked.connect(self.send_post)
        self.layout.addWidget(self.post_button)

    def send_post(self):
        self.post_button.setText("Отправка...")
        self.post_button.setEnabled(False)
        QApplication.processEvents()
        success = _send_to_telegram(self.image_pixmap, self.text)
        if success:
            QMessageBox.information(self, "Успех", "Пост успешно отправлен в Telegram!")
            self.close()
        else:
            self.post_button.setText("Запостить в Telegram")
            self.post_button.setEnabled(True)

def _send_to_telegram(image_pixmap, text):
    if "СЮДА_ВСТАВЬТЕ" in config.TELEGRAM_BOT_TOKEN:
        QMessageBox.critical(None, "Ошибка конфигурации", "Укажите TELEGRAM_BOT_TOKEN в файле config.py")
        return False
    try:
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not image_pixmap.save(buffer, "PNG"):
            raise ValueError("Не удалось подготовить изображение PNG")
        image_bytes = buffer.data().data()
        buffer.close()
        asyncio.run(_send_photo(image_bytes, text))
        return True
    except Exception as e:
        QMessageBox.critical(None, "Ошибка отправки", f"Не удалось отправить пост в Telegram:\n{e}")
        return False

async def _send_photo(image_bytes, text):
    async with telegram.Bot(token=config.TELEGRAM_BOT_TOKEN) as bot:
        with io.BytesIO(image_bytes) as photo_stream:
            await bot.send_photo(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                photo=photo_stream,
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
            )


def _generate_post_text(symbol, last_price, stop_loss, tp1, tp2):
    risk = abs(last_price - stop_loss)
    reward1 = abs(tp1 - last_price)
    rr_ratio_text = f"{(reward1 / risk):.2f} к 1 (до TP1)" if risk > 0 else "не определено"
    formatted_symbol = symbol.replace("USDT", "/USDT")
    post = (f"📈 *Сигнал по {formatted_symbol}* 📈\n\n"
            f"Прогноз на основе анализа 15-минутного графика.\n\n"
            f"*Параметры сделки:*\n"
            f"✅ *Точка входа (ориентировочно):* `{last_price}`\n"
            f"🎯 *Take-Profit 1:* `{tp1}`\n"
            f"🎯 *Take-Profit 2:* `{tp2}`\n"
            f"🚫 *Stop-Loss:* `{stop_loss}`\n\n"
            f"*Анализ рисков:*\n"
            f"📊 *Соотношение Риск/Прибыль:* `{rr_ratio_text}`\n\n"
            f"*Управление риском:*\n"
            f"⚠️ *Рекомендуемый вход:* `1-2% от депозита`")
    return post

def show_preview(parent, chart_image, symbol, last_price, stop_loss, tp1, tp2):
    post_text = _generate_post_text(symbol, last_price, stop_loss, tp1, tp2)
    dialog = _TelegramPreviewDialog(chart_image, post_text, parent)
    dialog.exec_()
