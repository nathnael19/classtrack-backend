from app.db.session import SessionLocal
from app.models.room import Room

def seed_rooms():
    db = SessionLocal()
    rooms = [
        {"name": "Lecture Hall 1", "building": "Engineering Block", "capacity": 200},
        {"name": "Computer Lab 3", "building": "IT Center", "capacity": 50},
        {"name": "Research Room 204", "building": "Science Wing", "capacity": 30},
        {"name": "Main Auditorium", "building": "Grand Hall", "capacity": 500},
        {"name": "Seminar Room B", "building": "Business School", "capacity": 40},
    ]
    
    for r in rooms:
        exists = db.query(Room).filter(Room.name == r["name"]).first()
        if not exists:
            db_room = Room(**r)
            db.add(db_room)
    
    db.commit()
    db.close()
    print("Rooms seeded successfully.")

if __name__ == "__main__":
    seed_rooms()
