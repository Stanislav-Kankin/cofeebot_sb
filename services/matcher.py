import logging
import random
from typing import List, Dict, Tuple
from database import Database  # ИСПРАВЛЕНО: убрал циклический импорт

logger = logging.getLogger(__name__)

class MatchMaker:
    def __init__(self, db: Database):
        self.db = db
    
    def calculate_match_score(self, user1: dict, user2: dict) -> Tuple[int, List[str]]:
        """Рассчитывает баллы совпадения и общие интересы"""
        score = 0
        common_interests = []
        
        # Базовые баллы за заполненность профиля
        score += 10
        
        # Совпадение по городу (+30 баллов)
        if user1.get('city') and user2.get('city'):
            if user1['city'].lower().strip() == user2['city'].lower().strip():
                score += 30
        
        # Совпадение по интересам
        interests1 = user1.get('interests', '')
        interests2 = user2.get('interests', '')
        
        if interests1 and interests2:
            interests1_set = set([i.strip().lower() for i in interests1.split(',') if i.strip()])
            interests2_set = set([i.strip().lower() for i in interests2.split(',') if i.strip()])
            
            common = interests1_set.intersection(interests2_set)
            if common:
                common_interests = list(common)
                score += len(common) * 15
        
        # Совпадение по целям
        goals1 = user1.get('goals', '')
        goals2 = user2.get('goals', '')
        
        if goals1 and goals2:
            goals1_set = set([g.strip().lower() for g in goals1.split(',') if g.strip()])
            goals2_set = set([g.strip().lower() for g in goals2.split(',') if g.strip()])
            common_goals = goals1_set.intersection(goals2_set)
            if common_goals:
                score += len(common_goals) * 10
        
        # Возрастная группа
        if user1.get('age') and user2.get('age'):
            age_diff = abs(user1['age'] - user2['age'])
            if age_diff <= 5:
                score += 20
            elif age_diff <= 10:
                score += 10
        
        return score, common_interests
    
    def have_previous_match(self, user1_id: int, user2_id: int) -> bool:
        """Проверяет, были ли пользователи уже в паре (любой статус)"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM matches 
                WHERE ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?))
            ''', (user1_id, user2_id, user2_id, user1_id))
            
            result = cursor.fetchone() is not None
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error checking previous matches: {e}")
            return True  # В случае ошибки считаем, что мэтч уже был
    
    def find_best_matches(self, user: dict, all_users: List[dict], max_matches: int = 3) -> List[Tuple[dict, int, List[str]]]:
        """Находит лучшие совпадения для пользователя"""
        matches = []
        
        for potential_match in all_users:
            if potential_match['user_id'] == user['user_id']:
                continue
            
            # Проверяем, не было ли уже мэтча (любого статуса)
            if self.have_previous_match(user['user_id'], potential_match['user_id']):
                continue
            
            score, common_interests = self.calculate_match_score(user, potential_match)
            
            # СНИЖАЕМ порог для создания мэтча ДО 0
            if score >= 0:  # был 5, теперь 0 - создаем любые пары
                matches.append((potential_match, score, common_interests))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:max_matches]
    
    def create_forced_match(self, user1_id: int, user2_id: int) -> bool:
        """Создает принудительный мэтч без проверки совпадений"""
        user1 = self.db.get_user(user1_id)
        user2 = self.db.get_user(user2_id)
        
        if not user1 or not user2:
            return False
            
        common_interests = ["случайное знакомство"]
        score = random.randint(10, 30)
        
        success = self.db.create_match(
            user1_id, user2_id, score, common_interests, is_forced=True
        )
        
        if success:
            logger.info(f"Created forced match between {user1_id} and {user2_id}")
        
        return success
    
    def run_matching_round(self, force_all: bool = False) -> int:
        """Запускает раунд мэтчинга"""
        active_users = self.db.get_all_active_users()
        
        if len(active_users) < 2:
            logger.info("Not enough users for matching")
            return 0
        
        logger.info(f"Starting matching round for {len(active_users)} users")
        
        # Перемешиваем пользователей для случайности
        random.shuffle(active_users)
        matched_user_ids = set()
        matches_created = 0
        
        # Используем два разных алгоритма в зависимости от режима
        if force_all:
            # Принудительный мэтчинг - просто создаем пары игнорируя предыдущие мэтчи
            for i in range(0, len(active_users) - 1, 2):
                user1 = active_users[i]
                user2 = active_users[i + 1]
                
                if user1['user_id'] in matched_user_ids or user2['user_id'] in matched_user_ids:
                    continue
                
                # Пропускаем проверку на предыдущие мэтчи в принудительном режиме
                # Создаем принудительный мэтч
                success = self.create_forced_match(user1['user_id'], user2['user_id'])
                
                if success:
                    matched_user_ids.add(user1['user_id'])
                    matched_user_ids.add(user2['user_id'])
                    matches_created += 1
                    logger.info(f"Created forced match between {user1['user_id']} and {user2['user_id']}")
        else:
            # Умный мэтчинг с поиском совпадений
            for user in active_users:
                if user['user_id'] in matched_user_ids:
                    continue
                
                # Ищем лучшие совпадения для текущего пользователя
                potential_matches = self.find_best_matches(
                    user, 
                    [u for u in active_users if u['user_id'] not in matched_user_ids and u['user_id'] != user['user_id']],
                    max_matches=1
                )
                
                if potential_matches:
                    partner, score, common_interests = potential_matches[0]
                    
                    # Создаем мэтч
                    success = self.db.create_match(
                        user['user_id'], partner['user_id'], score, common_interests, is_forced=False
                    )
                    
                    if success:
                        matched_user_ids.add(user['user_id'])
                        matched_user_ids.add(partner['user_id'])
                        matches_created += 1
                        logger.info(f"Created smart match between {user['user_id']} and {partner['user_id']} with score {score}")
            
            # Если остались неспаренные пользователи, создаем принудительные пары
            unmatched_users = [u for u in active_users if u['user_id'] not in matched_user_ids]
            logger.info(f"Unmatched users remaining: {len(unmatched_users)}")
            
            if len(unmatched_users) >= 2:
                # Создаем пары из оставшихся пользователей, игнорируя историю мэтчей
                for i in range(0, len(unmatched_users) - 1, 2):
                    user1 = unmatched_users[i]
                    user2 = unmatched_users[i + 1]
                    
                    success = self.create_forced_match(user1['user_id'], user2['user_id'])
                    if success:
                        matches_created += 1
                        logger.info(f"Created fallback forced match between {user1['user_id']} and {user2['user_id']}")
        
        logger.info(f"Matching round completed. Created {matches_created} matches")
        return matches_created
    
    def create_specific_match(self, user1_id: int, user2_id: int) -> bool:
        """Создает конкретный мэтч между двумя пользователями"""
        user1 = self.db.get_user(user1_id)
        user2 = self.db.get_user(user2_id)
        
        if not user1 or not user2:
            return False
        
        # Проверяем, не было ли уже мэтча
        if self.have_previous_match(user1_id, user2_id):
            return False
        
        score, common_interests = self.calculate_match_score(user1, user2)
        
        return self.db.create_match(user1_id, user2_id, score, common_interests)