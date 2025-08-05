import datetime
import os
import random
import re
import requests
import emoji
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from aiogram.enums import ParseMode
from bs4 import BeautifulSoup
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = "insert your token pls"

# массив кортежей названия фильма и времени его начала
# e.g. [('Лило и Стич', '22:00'), ('Люди в чёрном', '23:50')]
moviesTimesPairs = []

# Функция, которая будет обрабатывать команду /start
async def start(update: Update, context):
    await update.message.reply_text("use /today")

# Функция, которая будет писать в личку (пока что в личку) фильмы на сегодня
async def today(update: Update, context):
    await update.message.reply_text("loading...")
    images = createSeancesPictures() # массив путей к сгенеренным картинкам сеансов
    media = [InputMediaPhoto(open(image, 'rb')) for image in images] # массив картинок для сообщения в тг
    # массив разных эмоджи, из них выберется случайное
    emojiList = [':sparkling_heart:', ':heart_on_fire:', ':red_heart:', ':black_heart:', ':collision:', ':dizzy:',
                 ':thumbs_up:', ':eyes:', ':woman_dancing:', ':popcorn:', ':face_screaming_in_fear:', ':sunglasses:']

    # полноценное текстовое сообщение с эмоджи, списком фильмов и ссылкой на билеты
    todayMoviesListString = "\n".join(f"• {movie} - {movieTime}" for (movie, movieTime) in moviesTimesPairs)
    caption=f"Сегодня! {random.choice(emojiList)}\n\n<b>{todayMoviesListString}</b>\n\nБилеты: skylinecinema.ru"

    await update.message.reply_media_group(media, caption=emoji.emojize(caption), parse_mode=ParseMode.HTML)
    for image in images:
        os.remove(image) # удаление картинок с хранилища

# функция для разбиения текста на строки, понадобится для нанесения описания фильма на картинку
def splitText(text, font):
    words = text.split(" ")
    lines = []
    line = words[0]
    for word in words[1:]:
        if font.getbbox(line + " " + word)[2] <= 475: line += " " + word
        else:
            lines.append(line)
            line = word
    if line != "": lines.append(line)
    return lines

# функция для создания картинок сеансов
def createSeancesPictures():
    url = 'https://skylinecinema.ru'
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вc"] # массив дней недели в двухбуквенном формате

    # хватаем html-код
    html = requests.get(url).text

    today = days[datetime.date.today().weekday()]  # сегодняшний день недели

    # количество сеансов сегодня
    seances = 0

    # массивы с инфой по сеансам на сегодня, будут заполняться в цикле
    timesAndDates = []
    posters = []
    names = []
    ratings = []
    premiereYears = []
    chronos = []
    descriptions = []

    # поиск всех div-ов, репрезентующих сеансы
    # здесь и далее для параметра class_ метода find_all() я просто в инструментах разработчика в браузере поискал классы
    # тега div, в которых находится нужная мне инфа
    seancesDivs = BeautifulSoup(html, 'html.parser').find_all(
        'div',
        class_='grid auto-rows-max grid-flow-row md:rounded-lg gap-4 p-4 bg-white shadow md:max-w-xl hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700'
    )

    moviesTimesPairs.clear() # очистка массива на всякий случай
    for seanceDiv in seancesDivs:
        # собираем времена+дату сеансов
        timesNDatesTags = seanceDiv.find_all(
            class_='underline underline-offset-4 decoration-rose-600')
        timeNDateString = re.sub("  +", " ", timesNDatesTags[0].text.replace("\n", ""))  # дата и время сеанса сшиваются в строку с удалением лишних символов
        if today not in timeNDateString:
            break  # сегодняшний день отсутствует в строке => выход из цикла, ибо на сегодня сеансы кончились
        seances += 1  # подсчитываем количество сеансов
        timesAndDates.append(timeNDateString)

        # собираем постеры
        postersTags = seanceDiv.find_all('img')
        posterUrl = postersTags[0].get('src')
        posters.append(posterUrl)

        # собираем названия фильмов
        namesTags = seanceDiv.find_all('h5')
        name = re.sub("  +", "", namesTags[0].text.replace("\n", ""))  # содержимое тегов парсится с кучей лишних пробелов и \n
        names.append(name)

        # собираем рейтинги и года
        superTags = seanceDiv.find_all(class_='flex items-center gap-1')
        superString = re.sub("  +", "", superTags[0].text.replace("\n", " "))  # тут в одной строке и рейтинг, и год
        superString = " " + superString if len(superString.split(" ")) < 3 else superString
        rating, premiereYear = superString.split(" ")[:2]
        ratings.append(rating)
        premiereYears.append(premiereYear)

        # собираем хронометражи фильмов
        chronosTags = seanceDiv.find_all('time')
        chrono = re.sub("  +", " ", chronosTags[0].text.replace("\n", ""))[1:-1]
        chronos.append(chrono)
        moviesTimesPairs.append((name, chrono.split(' ')[0]))

        # собираем описания фильмов
        descriptionsTags = seanceDiv.find_all(class_='text-sm mt-2')
        description = re.sub("  +", "", descriptionsTags[0].text.replace("\n", " "))
        descriptions.append(description)

    paths = [] # пути к картинкам
    # в цикле будем создавать картинку для каждого сеанса
    for i in range(seances):
        # Задаем размеры изображения и цвет фона
        width, height = 1000, 600
        background_color = (31, 41, 55)

        # Создаем новое изображение
        image = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(image)
        textColor = (255, 255, 255)  # белый цвет текста

        # время и дата сеанса
        text = timesAndDates[i]
        font = ImageFont.truetype("arialbd.ttf", 40)
        draw.line((50, 73, int(font.getbbox(text)[2] + 30), 73), fill='red', width=3)
        draw.text((40, 30), text, textColor, font)

        # название фильма
        text = names[i]
        font = ImageFont.truetype("arialbd.ttf", 40) # Arial шрифт, уже не вспомню почему его выбрал
        textHeight = 100 # нужно для того, чтобы сдвинуть строчку с рейтингом, годом и хроно фильма, если его название занимает несколько строк
        for line in splitText(text, font):  # вот тут кстати текст наносится на картинку по строкам, чтобы он не выходил за границы картинки
            draw.text((500, textHeight), line, textColor, font)
            textHeight += font.getbbox(line)[3]
        movieDataHeight = textHeight + 15  # строчка с рейтингом и тп сдвигается, если название фильма в несколько строк
        font = ImageFont.truetype("arial.ttf", 20) # уменьшил размер шрифта

        # рейтинг, год и хронометраж
        if ratings[i] != '':
            draw.text((500, movieDataHeight), ratings[i], textColor, font) # рейтинг
            draw.text((560, movieDataHeight), premiereYears[i], textColor, font) # год
            draw.text((630, movieDataHeight), chronos[i], textColor, font) # хронометраж
        else:  # тут год и хроно сдвинул, чтобы пустого места не было при отсутствии рейтинга
            draw.text((500, movieDataHeight), premiereYears[i], textColor, font) # год
            draw.text((570, movieDataHeight), chronos[i], textColor, font) # хронометраж

        # описание фильма
        text = descriptions[i]
        textHeight = movieDataHeight + 75

        # вот тут кстати текст наносится на картинку по строкам, чтобы он не выходил за границы картинки
        for line in splitText(text, font):
            draw.text((500, textHeight), line, textColor, font)
            textHeight += font.getbbox(line)[3]

        # постер
        imageURL = posters[i]
        response = requests.get(imageURL)
        poster = Image.open(BytesIO(response.content))
        image.paste(poster.resize((poster.width * 500 // poster.height, 500)), (50, 100))

        # cохраняем картинку
        path = f"seance{i}.png"
        image.save(path)
        paths.append(path)
    return paths

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.run_polling()
