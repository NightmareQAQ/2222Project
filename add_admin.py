from routes import db
from models import User

db.create_all()
user1 = User(
            username='Amani',
            email='Amani@gmail.com',
            password='amaniamani',
            role='admin')
# user2 = User(
#             username='freya',
#             email='freya@gmail.com',
#             password='freyafreya',
#             role='admin')
db.session.add(user1)
# db.session.add(user2)
# user2 = User(
#             username='TomTomTom',
#             email='Tom@gmail.com',
#             password='tomtomtom')
# db.session.add(user2)
# user3 = User(
#             username='IreneIrene',
#             email='Irene@gmail.com',
#             password='ireneirene')
# db.session.add(user2)
# db.session.add(user3)
db.session.commit()