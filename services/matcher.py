import logging
import random
from typing import List, Dict, Tuple
from database import Database

logger = logging.getLogger(__name__)

class MatchMaker:
    def __init__(self, db: Database):
        self.db = db
    
    def calculate_match_score(self, user1: dict, user2: dict) -> Tuple[int, List[str]]:
        """Рассчитывает баллы совпадения и общие интересы"""
        score = 0
        common_interests = []
        
        # Совпадение по городу (+30 баллов)
        if user1.get('city') and user2.get('city'):
            if user1['city'].lower() == user2['city'].lower():
                score += 30
        
        # Совпадение по интересам
        interests1 = set([i.strip().lower() for i in user1.get('interests', '').split(',') if i.strip()])
        interests2 = set([i.strip().lower() for i in user2.get('interests', '').split(',') if i.strip()])
        
        common = interests1.intersection(interests2)
        if common:
            common_interests = list(common)
            score += len(common) * 15
        
        # Совпадение по целям
        if user1.get('goals') and user2.get('goals'):
            goals1 = set([g.strip().lower() for g in user1['goals'].split(',') if g.strip()])
            goals2 = set([g.strip().lower() for g in user2['goals'].split(',') if g.strip()])
            common_goals = goals1.intersection(goals2)
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
    
    def find_best_matches(self, user: dict, all_users: List[dict], max_matches: int = 3) -> List[Tuple[dict, int, List[str]]]:
        """Находит лучшие совпадения для пользователя"""
        matches = []
        
        for potential_match in all_users:
            if potential_match['user_id'] == user['user_id']:
                continue
            
            # Проверяем, не было ли уже мэтча
            existing_matches = self.db.get_pending_matches(user['user_id'])
            already_matched = any(
                m for m in existing_matches 
                if m['user1_id'] == potential_match['user_id'] or m['user2_id'] == potential_match['user_id']
            )
            
            if already_matched:
                continue
            
            score, common_interests = self.calculate_match_score(user, potential_match)
            
            if score >= 20:
                matches.append((potential_match, score, common_interests))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:max_matches]
    
    def create_forced_match(self, user1: dict, user2: dict) -> bool:
        """Создает принудительный мэтч без проверки совпадений"""
        common_interests = ["случайное знакомство"]
        score = random.randint(10, 30)
        
        success = self.db.create_match(
            user1['user_id'], user2['user_id'], score, common_interests, is_forced=True
        )
        
        if success:
            logger.info(f"Created forced match between {user1['user_id']} and {user2['user_id']}")
        
        return success
    
    def run_matching_round(self, force_all: bool = False) -> int:
        """Запускает раунд мэтчинга"""
        active_users = self.db.get_all_active_users()
        
        if len(active_users) < 2:
            logger.info("Not enough users for matching")
            return 0
        
        logger.info(f"Starting matching round for {len(active_users)} users")
        
        # Перемешиваем пользователей
        random.shuffle(active_users)
        matched_user_ids = set()
        matches_created = 0
        
        # Простой алгоритм - создаем пары по порядку
        for i in range(0, len(active_users) - 1, 2):
            user1 = active_users[i]
            user2 = active_users[i + 1]
            
            # Проверяем, не были ли уже сматчены
            if user1['user_id'] in matched_user_ids or user2['user_id'] in matched_user_ids:
                continue
            
            # Проверяем, нет ли уже существующего мэтча
            existing_matches = self.db.get_pending_matches(user1['user_id'])
            already_matched = any(
                m for m in existing_matches 
                if m['user1_id'] == user2['user_id'] or m['user2_id'] == user2['user_id']
            )
            
            if already_matched:
                continue
            
            if force_all:
                # Принудительный мэтч
                score = random.randint(10, 30)
                common_interests = ["случайное знакомство"]
                is_forced = True
            else:
                # Умный мэтч
                score, common_interests = self.calculate_match_score(user1, user2)
                is_forced = False
            
            # Создаем мэтч
            success = self.db.create_match(
                user1['user_id'], user2['user_id'], score, common_interests, is_forced
            )
            
            if success:
                matched_user_ids.add(user1['user_id'])
                matched_user_ids.add(user2['user_id'])
                matches_created += 1
                logger.info(f"Created match between {user1['user_id']} and {user2['user_id']}")
        
        logger.info(f"Matching round completed. Created {matches_created} matches")
        return matches_created
    
    def create_specific_match(self, user1_id: int, user2_id: int) -> bool:
        """Создает конкретный мэтч между двумя пользователями"""
        user1 = self.db.get_user(user1_id)
        user2 = self.db.get_user(user2_id)
        
        if not user1 or not user2:
            return False
        
        score, common_interests = self.calculate_match_score(user1, user2)
        
        return self.db.create_match(user1_id, user2_id, score, common_interests)