"""
routers/plants.py — Plant catalogue API
GET /api/plants       → list plants (filter, sort, paginate, search)
GET /api/plants/{id}  → single plant detail
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/plants", tags=["plants"])

PLANTS = [
    {"id":1,"name":"Monstera Deliciosa","sci":"Monstera deliciosa","emoji":"🌿","price":899,"oldPrice":1199,"img":"/plants-imgs/monstera-deliciosa-plant.avif","co2":2.1,"tags":["tropical","air","beginner"],"maint":"low","sun":"medium","water":"weekly","air":True,"pet":False,"isNew":False,"isSale":True,"rating":4.9,"rev":342,"climates":["tropical","subtropical","humid","temperate"],"minT":15,"maxT":35},
    {"id":2,"name":"Snake Plant","sci":"Sansevieria trifasciata","emoji":"🗡️","price":549,"img":"/plants-imgs/snake-plant.jpeg","co2":1.8,"tags":["air","beginner","low"],"maint":"low","sun":"low","water":"2 weeks","air":True,"pet":False,"isNew":False,"isSale":False,"rating":4.8,"rev":521,"climates":["tropical","subtropical","arid","temperate","cold","humid"],"minT":5,"maxT":40},
    {"id":3,"name":"Peace Lily","sci":"Spathiphyllum wallisii","emoji":"🕊️","price":699,"img":"/plants-imgs/peacelily.jpg","co2":1.5,"tags":["air","flowering"],"maint":"medium","sun":"low","water":"weekly","air":True,"pet":False,"isNew":True,"isSale":False,"rating":4.7,"rev":287,"climates":["tropical","subtropical","humid","temperate"],"minT":12,"maxT":30},
    {"id":4,"name":"Golden Pothos","sci":"Epipremnum aureum","emoji":"💛","price":349,"img":"/plants-imgs/Golden-Pothos-plant.png","co2":1.2,"tags":["air","beginner","low"],"maint":"low","sun":"low","water":"weekly","air":True,"pet":False,"isNew":False,"isSale":False,"rating":4.9,"rev":634,"climates":["tropical","subtropical","humid","temperate","arid"],"minT":10,"maxT":38},
    {"id":5,"name":"Spider Plant","sci":"Chlorophytum comosum","emoji":"🕷️","price":449,"img":"/plants-imgs/spider-plant.jpg","co2":1.6,"tags":["air","pet","beginner"],"maint":"low","sun":"medium","water":"weekly","air":True,"pet":True,"isNew":False,"isSale":False,"rating":4.7,"rev":398,"climates":["tropical","subtropical","temperate","cold"],"minT":5,"maxT":32},
    {"id":6,"name":"Fiddle Leaf Fig","sci":"Ficus lyrata","emoji":"🎻","price":1499,"img":"/plants-imgs/Fiddle-Leaf-Fig.webp","co2":2.8,"tags":["tropical"],"maint":"high","sun":"high","water":"weekly","air":False,"pet":False,"isNew":False,"isSale":False,"rating":4.5,"rev":189,"climates":["tropical","subtropical"],"minT":15,"maxT":30},
    {"id":7,"name":"ZZ Plant","sci":"Zamioculcas zamiifolia","emoji":"✨","price":649,"img":"/plants-imgs/zz-plant.webp","co2":1.4,"tags":["beginner","low"],"maint":"low","sun":"low","water":"2 weeks","air":False,"pet":False,"isNew":True,"isSale":False,"rating":4.8,"rev":276,"climates":["tropical","subtropical","arid","temperate"],"minT":8,"maxT":40},
    {"id":8,"name":"Rubber Plant","sci":"Ficus elastica","emoji":"🌱","price":799,"oldPrice":999,"img":"/plants-imgs/rubber-plant.jpg","co2":2.4,"tags":["air","tropical"],"maint":"medium","sun":"medium","water":"weekly","air":True,"pet":False,"isNew":False,"isSale":True,"rating":4.7,"rev":312,"climates":["tropical","subtropical","temperate"],"minT":10,"maxT":35},
    {"id":9,"name":"Bird of Paradise","sci":"Strelitzia reginae","emoji":"🦜","price":1849,"img":"/plants-imgs/Bird-of-paradise.jpg","co2":3.5,"tags":["tropical","flowering"],"maint":"medium","sun":"high","water":"weekly","air":False,"pet":False,"isNew":True,"isSale":False,"rating":4.8,"rev":89,"climates":["tropical","subtropical"],"minT":10,"maxT":38},
    {"id":10,"name":"Aloe Vera","sci":"Aloe barbadensis","emoji":"🌵","price":349,"img":"/plants-imgs/aloe-vera.jpg","co2":0.9,"tags":["beginner","low","succulent"],"maint":"low","sun":"high","water":"3 weeks","air":False,"pet":True,"isNew":False,"isSale":False,"rating":4.9,"rev":445,"climates":["arid","subtropical","temperate","tropical"],"minT":5,"maxT":42},
    {"id":11,"name":"Areca Palm","sci":"Dypsis lutescens","emoji":"🌴","price":1399,"img":"/plants-imgs/Areca%20Palm.jpg","co2":3.4,"tags":["air","pet","tropical"],"maint":"medium","sun":"medium","water":"twice weekly","air":True,"pet":True,"isNew":False,"isSale":False,"rating":4.7,"rev":203,"climates":["tropical","subtropical","humid"],"minT":12,"maxT":36},
    {"id":12,"name":"String of Pearls","sci":"Senecio rowleyanus","emoji":"🟢","price":499,"img":"/plants-imgs/String%20of%20Pearls.jpg","co2":0.7,"tags":["succulent","low"],"maint":"low","sun":"high","water":"3 weeks","air":False,"pet":False,"isNew":True,"isSale":False,"rating":4.6,"rev":167,"climates":["arid","subtropical","temperate"],"minT":5,"maxT":36},
    {"id":13,"name":"Calathea Orbifolia","sci":"Calathea orbifolia","emoji":"🌿","price":849,"img":"/plants-imgs/Calathea%20Orbifolia.jpg","co2":1.6,"tags":["tropical","pet"],"maint":"high","sun":"low","water":"weekly","air":False,"pet":True,"isNew":False,"isSale":False,"rating":4.5,"rev":134,"climates":["tropical","subtropical","humid"],"minT":13,"maxT":28},
    {"id":14,"name":"Philodendron Brasil","sci":"Philodendron hederaceum","emoji":"🍃","price":599,"oldPrice":749,"img":"/plants-imgs/Philodendron%20Brasil.jpg","co2":1.9,"tags":["beginner","tropical","air"],"maint":"low","sun":"medium","water":"weekly","air":True,"pet":False,"isNew":False,"isSale":True,"rating":4.8,"rev":298,"climates":["tropical","subtropical","humid","temperate"],"minT":10,"maxT":35},
    {"id":15,"name":"Orchid","sci":"Phalaenopsis amabilis","emoji":"🌺","price":649,"img":"/plants-imgs/Orchid%20plant.jpg","co2":0.8,"tags":["flowering","pet"],"maint":"medium","sun":"medium","water":"weekly","air":False,"pet":True,"isNew":False,"isSale":False,"rating":4.7,"rev":231,"climates":["tropical","subtropical","temperate"],"minT":15,"maxT":30},
    {"id":16,"name":"Echeveria","sci":"Echeveria elegans","emoji":"🌸","price":249,"img":"/plants-imgs/Echeveria%20plant.jpg","co2":0.5,"tags":["succulent","low","beginner"],"maint":"low","sun":"high","water":"3 weeks","air":False,"pet":False,"isNew":False,"isSale":False,"rating":4.8,"rev":389,"climates":["arid","subtropical","temperate"],"minT":2,"maxT":38},
    {"id":17,"name":"Boston Fern","sci":"Nephrolepis exaltata","emoji":"🌿","price":599,"img":"/plants-imgs/Boston%20Fern.jpg","co2":2.0,"tags":["air","pet"],"maint":"medium","sun":"medium","water":"twice weekly","air":True,"pet":True,"isNew":False,"isSale":True,"rating":4.6,"rev":198,"climates":["tropical","subtropical","humid","temperate"],"minT":8,"maxT":30},
    {"id":18,"name":"Jade Plant","sci":"Crassula ovata","emoji":"🍃","price":429,"img":"/plants-imgs/Jade%20Plant.jpg","co2":1.0,"tags":["succulent","beginner","low"],"maint":"low","sun":"high","water":"3 weeks","air":False,"pet":False,"isNew":False,"isSale":False,"rating":4.7,"rev":312,"climates":["arid","subtropical","temperate"],"minT":5,"maxT":35},
    {"id":19,"name":"Dracaena Marginata","sci":"Dracaena marginata","emoji":"🌴","price":899,"img":"/plants-imgs/Dracaena%20Marginata.jpg","co2":2.2,"tags":["air","beginner"],"maint":"low","sun":"medium","water":"2 weeks","air":True,"pet":False,"isNew":False,"isSale":False,"rating":4.6,"rev":187,"climates":["tropical","subtropical","temperate"],"minT":10,"maxT":35},
    {"id":20,"name":"Anthurium","sci":"Anthurium andraeanum","emoji":"❤️","price":799,"img":"/plants-imgs/Anthurium%20plant.jpg","co2":1.3,"tags":["flowering","air"],"maint":"medium","sun":"medium","water":"weekly","air":True,"pet":False,"isNew":False,"isSale":True,"rating":4.7,"rev":223,"climates":["tropical","subtropical","humid"],"minT":15,"maxT":32},
    {"id":21,"name":"Tulsi","sci":"Ocimum tenuiflorum","emoji":"🌿","price":149,"img":"/plants-imgs/Tulsi%20plant.jpg","co2":0.6,"tags":["herb","beginner","pet"],"maint":"low","sun":"high","water":"twice weekly","air":True,"pet":True,"isNew":False,"isSale":False,"rating":4.9,"rev":876,"climates":["tropical","subtropical","temperate"],"minT":10,"maxT":40},
    {"id":22,"name":"Mint","sci":"Mentha spicata","emoji":"🌱","price":129,"img":"/plants-imgs/Mint%20plant.jpg","co2":0.5,"tags":["herb","beginner","pet"],"maint":"low","sun":"medium","water":"twice weekly","air":False,"pet":True,"isNew":False,"isSale":False,"rating":4.8,"rev":654,"climates":["temperate","subtropical","tropical"],"minT":5,"maxT":35},
    {"id":23,"name":"Curry Leaf Plant","sci":"Murraya koenigii","emoji":"🍃","price":249,"img":"/plants-imgs/Curry%20Leaf%20Plant.jpg","co2":0.9,"tags":["herb"],"maint":"low","sun":"high","water":"twice weekly","air":False,"pet":True,"isNew":False,"isSale":False,"rating":4.9,"rev":534,"climates":["tropical","subtropical"],"minT":12,"maxT":42},
    {"id":24,"name":"Money Plant","sci":"Epipremnum aureum","emoji":"💰","price":199,"img":"/plants-imgs/Money%20Plant.jpg","co2":1.2,"tags":["indoor","air","beginner"],"maint":"low","sun":"low","water":"weekly","air":True,"pet":False,"isNew":False,"isSale":False,"rating":4.9,"rev":1023,"climates":["tropical","subtropical","temperate","humid"],"minT":8,"maxT":40},
]


@router.get("/")
def get_plants(
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    limit: int = 12,
    q: Optional[str] = None,
):
    plant_list = list(PLANTS)

    # Text search
    if q:
        query = q.lower()
        plant_list = [
            p for p in plant_list
            if query in p["name"].lower()
            or query in p["sci"].lower()
            or any(query in t.lower() for t in p["tags"])
        ]

    # Category filter
    if filter and filter != "all":
        if filter == "air":
            plant_list = [p for p in plant_list if p["air"]]
        elif filter == "pet":
            plant_list = [p for p in plant_list if p["pet"]]
        elif filter == "low":
            plant_list = [p for p in plant_list if p["maint"] == "low"]
        elif filter == "beginner":
            plant_list = [p for p in plant_list if "beginner" in p["tags"]]
        else:
            plant_list = [p for p in plant_list if filter in p["tags"]]

    # Sort
    if sort == "price-asc":
        plant_list.sort(key=lambda p: p["price"])
    elif sort == "price-desc":
        plant_list.sort(key=lambda p: p["price"], reverse=True)
    elif sort == "name":
        plant_list.sort(key=lambda p: p["name"])
    elif sort == "rating":
        plant_list.sort(key=lambda p: p["rating"], reverse=True)
    elif sort == "co2":
        plant_list.sort(key=lambda p: p["co2"], reverse=True)

    total = len(plant_list)
    page_num = max(1, page)
    limit_num = min(50, max(1, limit))
    offset = (page_num - 1) * limit_num
    paginated = plant_list[offset: offset + limit_num]

    import math
    return {
        "plants": paginated,
        "total": total,
        "page": page_num,
        "limit": limit_num,
        "pages": math.ceil(total / limit_num) if total else 1,
    }


@router.get("/{plant_id}")
def get_plant(plant_id: int):
    plant = next((p for p in PLANTS if p["id"] == plant_id), None)
    if not plant:
        from fastapi import HTTPException
        raise HTTPException(404, "Plant not found")

    related = [p for p in PLANTS if p["id"] != plant_id and any(t in plant["tags"] for t in p["tags"])][:4]
    return {"plant": plant, "related": related}
