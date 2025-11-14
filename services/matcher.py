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
            score += len(common) * 10  # +10 баллов за каждый общий интерес
        
        # Совпадение по целям
        if user1.get('goals') and user2.get('goals'):
            goals1 = set([g.strip().lower() for g in user1['goals'].split(',') if g.strip()])
            goals2 = set([g.strip().lower() for g in user2['goals'].split(',') if g.strip()])
            if goals1.intersection(goals2):
                score += 20
        
        # Возрастная группа (разница до 5 лет +20 баллов, до 10 лет +10)
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
            
            score, common_interests = self.calculate_match_score(user, potential_match)
            
            if score >= 20:  # Минимальный порог для мэтча
                matches.append((potential_match, score, common_interests))
        
        # Сортируем по баллам и берем лучшие
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:max_matches]
    
    def run_matching_round(self):
        """Запускает раунд мэтчинга для всех активных пользователей"""
        active_users = self.db.get_all_active_users()
        matched_pairs = set()
        
        logger.info(f"Starting matching round for {len(active_users)} users")
        
        for user in active_users:
            if user['user_id'] in matched_pairs:
                continue
            
            # Исключаем уже совпавших пользователей
            available_users = [u for u in active_users if u['user_id'] not in matched_pairs and u['user_id'] != user['user_id']]
            
            if not available_users:
                continue
            
            best_matches = self.find_best_matches(user, available_users, max_matches=1)
            
            if best_matches:
                match_user, score, common_interests = best_matches[0]
                
                # Создаем мэтч в базе
                success = self.db.create_match(user['user_id'], match_user['user_id'], score, common_interests)
                
                if success:
                    matched_pairs.add(user['user_id'])
                    matched_pairs.add(match_user['user_id'])
                    logger.info(f"Created match between {user['user_id']} and {match_user['user_id']} with score {score}")
        
        logger.info(f"Matching round completed. Created {len(matched_pairs) // 2} matches")
        return len(matched_pairs) // 2