FROM python:3.7.3

RUN mkdir /metro-tenerife-bot
COPY . /metro-tenerife-bot
WORKDIR /metro-tenerife-bot
RUN pip install --user -r requirements.txt
CMD [ "python", "metro_tenerife_bot.py" ]