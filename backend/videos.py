"""Built-in video instructions for the exercise catalog (YouTube).

The key is the exercise name, the value is the video id. The links were checked: the videos exist and allow embedding."""
import re

EXERCISE_VIDEOS = {
    "Болгарські присідання": "or1frhkjBDc",
    "Жим лежачи": "hWbUlkb5Ms4",
    "Жим гантелей лежачи": "1V3vpcaxRYQ",
    "Жим стоячи": "4LBVP2Oe7fg",
    "Присідання зі штангою": "gcNh17Ckjgg",
    "Фронтальні присідання": "_qv0m3tPd3s",
    "Станова тяга": "ZaTM37cfiDs",
    "Румунська тяга": "_oyxCn2iSjU",
    "Тяга штанги в нахилі": "phVtqawIgbk",
    "Підтягування": "eGo4IYlbE5g",
    "Віджимання на брусах": "T1L4smOP0L8",
    "Віджимання від підлоги": "c-lBErfxszs",
    "Тяга верхнього блоку": "bNmvKpJSWKM",
    "Тяга нижнього блоку": "vwHG9Jfu4sw",
    "Підйом на біцепс": "MKWBV29S6c0",
    "Французький жим": "K3mFeNz4e3w",
    "Розведення гантелей": "Nhvz9EzdJ4U",
    "Випади": "Pbmj6xPo-Hw",
    "Жим ногами": "nDh_BlnLCGc",
    "Підйом на носки": "eMTy3qylqnE",
    "Планка": "xe2MXatLTUw",
    "Скручування": "MKmrqcoCZ-M",
    "Махи гирею": "aSYap2yhW8s",
    "Гіперекстензія": "9XN23dIEqLE",
    "Ривок штанги": "fVfFaTxXucM",
    "Поштовх штанги": "RP1094HlQOQ",
}

assert all(re.fullmatch(r"[A-Za-z0-9_-]{11}", i) for i in EXERCISE_VIDEOS.values())


def video_items():
    return [{"exercise": name, "name_key": name.casefold(), "video_id": vid} for name, vid in EXERCISE_VIDEOS.items()]
