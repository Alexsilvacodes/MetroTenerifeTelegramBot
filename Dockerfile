FROM python:3.8

RUN mkdir /metro-tenerife-bot
COPY . /metro-tenerife-bot
WORKDIR /metro-tenerife-bot
RUN pip install --upgrade pip &&\
    pip install --user -r requirements.txt
CMD [ "python", "metro_tenerife_bot.py" ]
