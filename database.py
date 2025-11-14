import sqlite3
import datetime
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "random_coffee.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Инициализация всех таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                age INTEGER,
                city TEXT,
                profession TEXT,
                interests TEXT,
                goals TEXT,
                about TEXT,
                contact_preference TEXT,
                registration_date TEXT,
                last_active TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                matches_count INTEGER DEFAULT 0,
                profile_completed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Таблица вопросов анкеты
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT,
                question_order INTEGER,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Таблица мэтчей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER,
                user2_id INTEGER,
                match_score INTEGER,
                common_interests TEXT,
                status TEXT DEFAULT 'pending',
                created_date TEXT,
                accepted_date TEXT,
                is_forced BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user1_id) REFERENCES users (user_id),
                FOREIGN KEY (user2_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица действий пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                target_user_id INTEGER,
                action_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица запланированных мэтчей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date TEXT,
                status TEXT DEFAULT 'scheduled',
                created_date TEXT,
                completed_date TEXT
            )
        ''')
        
        # Добавляем стандартные вопросы
        default_questions = [
            ("Как тебя зовут?", 1),
            ("Сколько тебе лет?", 2),
            ("Из какого ты города?", 3),
            ("Чем занимаешься (профессия/род деятельности)?", 4),
            ("Какие у тебя интересы/хобби? (перечисли через запятую)", 5),
            ("Что ищешь в Random Coffee? (новые знакомства, бизнес-контакты, друзья)", 6),
            ("Расскажи о себе кратко", 7),
            ("Как предпочитаешь общаться? (Telegram, email, другое)", 8)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM questions")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO questions (question_text, question_order) VALUES (?, ?)",
                default_questions
            )
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    # === USER METHODS ===
    def add_user(self, user_id: int, username: str = None) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Сначала проверяем, существует ли пользователь
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Обновляем username и last_active если пользователь уже существует
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, last_active = ?
                    WHERE user_id = ?
                ''', (
                    username,
                    datetime.datetime.now().isoformat(),
                    user_id
                ))
                logger.info(f"Updated existing user: {user_id}")
            else:
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users 
                    (user_id, username, registration_date, last_active)
                    VALUES (?, ?, ?, ?)
                ''', (
                    user_id,
                    username,
                    datetime.datetime.now().isoformat(),
                    datetime.datetime.now().isoformat()
                ))
                logger.info(f"Created new user: {user_id}")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding/updating user: {e}")
            return False
    
    def update_user_profile(self, user_id: int, **kwargs) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(user_id)
            
            query = f"UPDATE users SET {set_clause}, profile_completed = TRUE WHERE user_id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_all_active_users(self) -> List[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE is_active = TRUE AND profile_completed = TRUE")
            rows = cursor.fetchall()
            conn.close()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_questions(self) -> List[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE is_active = TRUE ORDER BY question_order")
            rows = cursor.fetchall()
            conn.close()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting questions: {e}")
            return []
    
    # === MATCH METHODS ===
    def create_match(self, user1_id: int, user2_id: int, match_score: int, common_interests: List[str], is_forced: bool = False) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже существующего мэтча
            cursor.execute('''
                SELECT id FROM matches 
                WHERE ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?))
                AND status != 'rejected'
            ''', (user1_id, user2_id, user2_id, user1_id))
            
            if cursor.fetchone():
                return False  # Мэтч уже существует
            
            cursor.execute('''
                INSERT INTO matches 
                (user1_id, user2_id, match_score, common_interests, status, created_date, is_forced)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user1_id,
                user2_id,
                match_score,
                json.dumps(common_interests),
                'pending',
                datetime.datetime.now().isoformat(),
                is_forced
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            return False
    
    def get_pending_matches(self, user_id: int) -> List[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, 
                       CASE 
                           WHEN m.user1_id = ? THEN u2.name 
                           ELSE u1.name 
                       END as partner_name,
                       CASE 
                           WHEN m.user1_id = ? THEN u2.username 
                           ELSE u1.username 
                       END as partner_username
                FROM matches m
                LEFT JOIN users u1 ON m.user1_id = u1.user_id
                LEFT JOIN users u2 ON m.user2_id = u2.user_id
                WHERE (m.user1_id = ? OR m.user2_id = ?) 
                AND m.status = 'pending'
            ''', (user_id, user_id, user_id, user_id))
            
            rows = cursor.fetchall()
            conn.close()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting pending matches: {e}")
            return []
    
    def update_match_status(self, match_id: int, status: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE matches 
                SET status = ?, accepted_date = ?
                WHERE id = ?
            ''', (status, datetime.datetime.now().isoformat() if status == 'accepted' else None, match_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating match status: {e}")
            return False
    
    def get_all_pending_matches(self) -> List[dict]:
        """Получить все pending мэтчи для админа"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, u1.name as user1_name, u2.name as user2_name,
                       u1.username as user1_username, u2.username as user2_username
                FROM matches m
                LEFT JOIN users u1 ON m.user1_id = u1.user_id
                LEFT JOIN users u2 ON m.user2_id = u2.user_id
                WHERE m.status = 'pending'
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all pending matches: {e}")
            return []
    
    # === SCHEDULED MATCHES ===
    def create_scheduled_match(self, match_date: str) -> int:
        """Создает запланированный мэтч и возвращает его ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO scheduled_matches (match_date, created_date)
                VALUES (?, ?)
            ''', (match_date, datetime.datetime.now().isoformat()))
            
            match_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return match_id
        except Exception as e:
            logger.error(f"Error creating scheduled match: {e}")
            return -1
    
    def get_scheduled_matches(self) -> List[dict]:
        """Получить все запланированные мэтчи"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM scheduled_matches 
                ORDER BY match_date DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting scheduled matches: {e}")
            return []
    
    def update_scheduled_match_status(self, match_id: int, status: str):
        """Обновить статус запланированного мэтча"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE scheduled_matches 
                SET status = ?, completed_date = ?
                WHERE id = ?
            ''', (status, datetime.datetime.now().isoformat() if status == 'completed' else None, match_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating scheduled match: {e}")
            return False
    
    # === ANALYTICS METHODS ===
    def get_user_stats(self) -> dict:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            active_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE profile_completed = TRUE")
            completed_profiles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'accepted'")
            successful_matches = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'pending'")
            pending_matches = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM scheduled_matches WHERE status = 'scheduled'")
            scheduled_matches = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'completed_profiles': completed_profiles,
                'successful_matches': successful_matches,
                'pending_matches': pending_matches,
                'scheduled_matches': scheduled_matches
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    def log_user_action(self, user_id: int, action_type: str, target_user_id: int = None):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_actions (user_id, action_type, target_user_id, action_date)
                VALUES (?, ?, ?, ?)
            ''', (user_id, action_type, target_user_id, datetime.datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging user action: {e}")
    
    def init_db(self):
        """Инициализация всех таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                age INTEGER,
                city TEXT,
                profession TEXT,
                interests TEXT,
                goals TEXT,
                about TEXT,
                contact_preference TEXT,
                registration_date TEXT,
                last_active TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                matches_count INTEGER DEFAULT 0,
                profile_completed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Таблица мэтчей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER,
                user2_id INTEGER,
                match_score INTEGER,
                common_interests TEXT,
                status TEXT DEFAULT 'pending',
                created_date TEXT,
                accepted_date TEXT,
                is_forced BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user1_id) REFERENCES users (user_id),
                FOREIGN KEY (user2_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица запланированных мэтчей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_date TEXT,
                status TEXT DEFAULT 'scheduled',
                created_date TEXT,
                completed_date TEXT
            )
        ''')
        
        # Таблица действий пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                target_user_id INTEGER,
                action_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица вопросов анкеты
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT,
                question_order INTEGER,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Добавляем стандартные вопросы
        default_questions = [
            ("Как тебя зовут?", 1),
            ("Сколько тебе лет?", 2),
            ("Из какого ты города?", 3),
            ("Чем занимаешься (профессия/род деятельности)?", 4),
            ("Какие у тебя интересы/хобби? (перечисли через запятую)", 5),
            ("Что ищешь в Random Coffee? (новые знакомства, бизнес-контакты, друзья)", 6),
            ("Расскажи о себе кратко", 7),
            ("Как предпочитаешь общаться? (Telegram, email, другое)", 8)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM questions")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO questions (question_text, question_order) VALUES (?, ?)",
                default_questions
            )
        
        # Проверяем и добавляем отсутствующие колонки
        self._update_table_structure(cursor, "matches", "is_forced", "BOOLEAN DEFAULT FALSE")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def _update_table_structure(self, cursor, table_name, column_name, column_type):
        """Добавляет колонку в таблицу если она отсутствует"""
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                logger.info(f"Added column {column_name} to table {table_name}")
        except Exception as e:
            logger.error(f"Error updating table structure: {e}")