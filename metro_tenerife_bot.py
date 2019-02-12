#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import logging

from bs4 import BeautifulSoup
import requests, json
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


"""
Metro Tenerife parser
"""

def requestData():
    url = "http://tranviaonline.metrotenerife.com/#paneles"

    req = requests.get(url)
    html = req.text
    soup = BeautifulSoup(html, "html.parser")
    script_tags = soup.find_all("script")
    data = ""
    for script in script_tags:
        if "lines" in str(script.string):
            data = script

    data_splited = data.string.split(";")

    stops_string = ""
    lines_string = ""
    panels_string = ""
    for item in data_splited:
        if "var stops" in item:
            stops_string = item
            stops_string = stops_string.replace("var stops = ", "")
        elif "var lines" in item:
            lines_string = item
            lines_string = lines_string.replace("var lines = ", "")
        elif "var panels" in item:
            panels_string = item
            panels_string = panels_string.replace("var panels = ", "")

    lines = json.loads(lines_string)
    stops = json.loads(stops_string)
    panels = json.loads(panels_string)

    return (lines, stops, panels)


def formatLines(lines, lang="es"):
    lines_res = []

    for line in lines:
        name = ""
        if lang is "es":
            name = "Línea " + line["id"]
        else:
            name = "Line " + line["id"]
        destinations = line["destinations"][0]["name"] + " - " + line["destinations"][-1]["name"]
        lines_res.append({"name": name, "destinations": destinations})

    return lines_res


def formatStops(stops, line, lang="es"):
    stops_res = []
    stops_aux = []

    for stop in stops:
        if line in stop["lines"]:
            stops_aux.append(stop)

    for stop in stops_aux:
        stops_res.append({"id": stop["id"], "name": stop["name"]})

    return stops_aux


def formatPanels(panels, line, stop, lang="es"):
    panels_aux = []
    panels_res = []
    panels_last_update = ""

    for panel in panels:
        if line == panel["route"] and stop == panel["stop"]:
            panels_aux.append(panel)

    panels_aux = sorted(panels_aux, key=lambda x: x["remainingMinutes"])
    if len(panels_aux) > 4:
        panels_aux = panels_aux[0:4]

    for panel in panels_aux:
        panels_last_update = panel["lastUpdateFormatted"]
        if lang is "es":
            panels_res.append({
                "to": "🚇 > " + panel["destinationStopDescription"],
                "remaining": "🕓 > Faltan " + str(panel["remainingMinutes"]) + " minutos"
                })
        else:
            panels_res.append({
                "to": "🚇 > " + panel["destinationStopDescription"],
                "remaining": "🕓 > " + str(panel["remainingMinutes"]) + " minutes remaining"
                })

    return panels_res, panels_last_update


"""
Telegram related methods
"""


def start(bot, update, user_data):
    user_data["lang"] = "en"
    update.message.reply_text("To use this bot in english call /en\n===================\nPara usar el bot en castellano use /es")


def spanish(bot, update, user_data):
    user_data["lang"] = "es"
    update.message.reply_text("Use /start para iniciar el bot.\nUse /nexttram para obtener información acerca del siguiente tranvía por cada parada.\nUse /lastStop para obtener información de la última parada seleccionada.")


def english(bot, update, user_data):
    user_data["lang"] = "en"
    update.message.reply_text("Use /start to test this bot.\nUse /nexttram to get info about the next tram for each stop.\nUse /lastStop to get info about the last stop selected.")

def lastStop(bot, update, user_data):
    query = update.callback_query
    lang = user_data["lang"]
    try:
        stop = user_data["stop"]
        line = user_data["line"]

        lines, stops, panels = requestData()
        if len(panels) > 0:
            panelsFormatted, last_update = formatPanels(panels, line, stop, lang=lang)
            stopsFormatted = formatStops(stops, line)
            stopName = ""
            for stopItem in stopsFormatted:
                if stopItem["id"] == stop:
                    stopName = stopItem["name"]
            if len(panelsFormatted) > 0:
                reply = ""
                if lang == "es":
                    reply = "Próximos tranvías en *" + stopName + "*\n\n"
                else:
                    reply = "Oncoming trams for *" + stopName + "*\n\n"
                for panel in panelsFormatted:
                    reply = reply + panel["to"] + "\n" + panel["remaining"] + "\n\n"
                reply = reply + "_" + last_update + "_ (GMT)"
                bot.send_message(text=reply,
                                chat_id=query.message.chat_id,
                                message_id=query.message.message_id,
                                parse_mode= "Markdown")

    except KeyError:
        text = ""
        if lang == "es":
            text = "Ha ocurrido un error al solicitar los datos 🙁"
        else:
            text = "There was some error requesting tram data 🙁"
        bot.send_message(text=text,
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id)

def requestInfo(bot, update, user_data):
    lang = user_data["lang"]
    lines, stops, panels = requestData()
    linesFormatted = formatLines(lines, lang=lang)
    keyboard = []

    i = 1
    for line in linesFormatted:
        keyboard.append(InlineKeyboardButton(line["name"], callback_data="line/" + str(i)))
        i += 1

    reply_markup = InlineKeyboardMarkup([keyboard])

    text = ""
    if lang == "es":
        text = "Por favor, seleccione la línea de tranvía 🚇"
    else:
        text = "Please choose the tram line 🚇"
    update.message.reply_text(text, reply_markup=reply_markup)
    
def requestLastQueriedStopInfo(bot, update):
    query = update.callback_query
    lines, stops, panels = requestData()
    line = last_line
    stop = last_stop
    if len(panels) > 0:
        panelsFormatted, last_update = formatPanels(panels, line, stop, lang=lang)
        stopsFormatted = formatStops(stops, line)
        stopName = ""
        for stopItem in stopsFormatted:
            if stopItem["id"] == stop:
                stopName = stopItem["name"]
        if len(panelsFormatted) > 0:
            reply = ""
            if lang == "es":
                reply = "Próximos tranvías en *" + stopName + "*\n\n"
            else:
                reply = "Oncoming trams for *" + stopName + "*\n\n"
            for panel in panelsFormatted:
                reply = reply + panel["to"] + "\n" + panel["remaining"] + "\n\n"
            reply = reply + "_" + last_update + "_ (GMT)"
            update.message.reply_text(reply, parse_mode= "Markdown")


def button(bot, update, user_data):
    lang = user_data["lang"]
    query = update.callback_query
    data = query.data
    type = data.split("/")[0]

    bot.deleteMessage(chat_id=query.message.chat_id, message_id=query.message.message_id)

    if type == "line":
        line = int(data.split("/")[1])
        user_data["line"] = line
        lines, stops, panels = requestData()
        if len(stops) > 0:
            stopsFormatted = formatStops(stops, line)
            if len(stopsFormatted) > 0:
                keyboard = []
                keyboard_row = []
                i = 0
                for stop in stopsFormatted:
                    i += 1
                    keyboard_row.append(InlineKeyboardButton(stop["name"], callback_data="stop/" + stop["id"] + "/" + str(line)))
                    if i == 2:
                        keyboard.append(keyboard_row)
                        keyboard_row = []
                        i = 0

                reply_markup = InlineKeyboardMarkup(keyboard)
                text = ""
                if lang == "es":
                    text = "Por favor, seleccione la parada de la que desea información 📊"
                else:
                    text = "Please, choose the stop from which you need info 📊"
                bot.send_message(text=text,
                                chat_id=query.message.chat_id,
                                message_id=query.message.message_id,
                                reply_markup=reply_markup)
    elif type == "stop":
        stop = data.split("/")[1]
        user_data["stop"] = stop
        line = int(data.split("/")[2])
        lines, stops, panels = requestData()
        if len(panels) > 0:
            panelsFormatted, last_update = formatPanels(panels, line, stop, lang=lang)
            stopsFormatted = formatStops(stops, line)
            stopName = ""
            for stopItem in stopsFormatted:
                if stopItem["id"] == stop:
                    stopName = stopItem["name"]
            if len(panelsFormatted) > 0:
                reply = ""
                if lang == "es":
                    reply = "Próximos tranvías en *" + stopName + "*\n\n"
                else:
                    reply = "Oncoming trams for *" + stopName + "*\n\n"
                for panel in panelsFormatted:
                    reply = reply + panel["to"] + "\n" + panel["remaining"] + "\n\n"
                reply = reply + "_" + last_update + "_ (GMT)"
                bot.send_message(text=reply,
                                chat_id=query.message.chat_id,
                                message_id=query.message.message_id,
                                parse_mode= "Markdown")
    else:
        text = ""
        if lang == "es":
            text = "Ha ocurrido un error al solicitar los datos 🙁"
        else:
            text = "There was some error requesting tram data 🙁"
        bot.send_message(text=text,
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id)


def help(bot, update, user_data):
    help = ""
    if user_data["lang"] == "es":
        help = "Use /start para iniciar el bot.\nUse /nexttram para obtener información acerca del siguiente tranvía por cada parada.\nUse /lastStop para obtener información de la última parada seleccionada."
    else:
        help = "Use /start to test this bot.\nUse /nexttram to get info about the next tram for each stop.\nUse /lastStop to get info about the last stop selected."

    update.message.reply_text(help)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    token = ""
    is_prod = os.environ.get('IS_HEROKU', None)
    if is_prod:
        token = os.environ.get('TOKEN', None)
    else:
        f_token = open("token", "r")
        token = f_token.read().rstrip("\n")
        f_token.close()
    updater = Updater(token)

    updater.dispatcher.add_handler(CommandHandler("start", start, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler("es", spanish, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler("en", english, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler("nexttram", requestInfo, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler("laststop", lastStop, pass_user_data=True))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler("help", help, pass_user_data=True))
    updater.dispatcher.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
