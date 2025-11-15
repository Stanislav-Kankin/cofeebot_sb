import os
from database import Database

def reset_database():
    """Пересоздает базу данных с новой структурой"""
    if os.path.exists("random_coffee.db"):
        os.remove("random_coffee.db")
        print("✅ Старая база данных удалена")
    
    db = Database()
    print("✅ Новая база данных создана")
    
    # Добавляем тестовых пользователей (с заполненными профилями)

    test_users = [
        {
            'user_id': 123456789,
            'username': 'admin_user', 
            'name': 'Админ',
            'age': 30,
            'city': 'Москва',
            'profession': 'Разработчик',
            'interests': 'программирование, AI, стартапы',
            'goals': 'бизнес-контакты, менторство',
            'about': 'Люблю создавать интересные проекты',
            'linkedin_url': 'https://linkedin.com/in/adminuser',
            'contact_preference': 'Telegram'
        },
        {
            'user_id': 987654321,
            'username': 'user1',
            'name': 'Иван',
            'age': 25,
            'city': 'Санкт-Петербург', 
            'profession': 'Дизайнер',
            'interests': 'дизайн, искусство, путешествия',
            'goals': 'новые знакомства, коллаборации',
            'about': 'Увлекаюсь UI/UX дизайном',
            'linkedin_url': 'https://linkedin.com/in/ivan',
            'contact_preference': 'Telegram'
        },
        {
            'user_id': 555555555,
            'username': 'user2', 
            'name': 'Мария',
            'age': 28,
            'city': 'Москва',
            'profession': 'Маркетолог',
            'interests': 'маркетинг, книги, йога',
            'goals': 'нетворкинг, друзья',
            'about': 'Работаю в digital-маркетинге',
            'linkedin_url': 'https://linkedin.com/in/maria',
            'contact_preference': 'Email'
        }
    ]
    
    for user_data in test_users:
        user_id = user_data['user_id']
        username = user_data['username']
        
        # Добавляем пользователя
        db.add_user(user_id, username)
        
        # Заполняем профиль
        success = db.update_user_profile(
            user_id=user_id,
            name=user_data['name'],
            age=user_data['age'],
            city=user_data['city'],
            profession=user_data['profession'],
            interests=user_data['interests'],
            goals=user_data['goals'],
            about=user_data['about'],
            contact_preference=user_data['contact_preference']
        )
        
        if success:
            print(f"✅ Добавлен пользователь: {user_data['name']}")
        else:
            print(f"❌ Ошибка при добавлении: {user_data['name']}")
    
    print("✅ Тестовые пользователи добавлены с заполненными профилями")

if __name__ == "__main__":
    reset_database()