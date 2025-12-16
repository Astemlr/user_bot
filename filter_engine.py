"""Движок фильтрации сообщений."""
import re
import aiohttp
import json
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from torch.nn.functional import cosine_similarity
from config import (
    SEMANTIC_PROVIDER, SEMANTIC_MODEL, SEMANTIC_THRESHOLD,
    OPENROUTER_API_KEY, OPENROUTER_MODEL,
    YANDEX_API_KEY, YANDEX_FOLDER_ID,
    OPENAI_API_KEY, OPENAI_MODEL
)


class FilterEngine:
    """Движок для фильтрации сообщений по ключевым словам и семантике."""

    def __init__(self):
        """Инициализация движка фильтрации."""
        self.semantic_model = None
        self.semantic_initialized = False
        self.semantic_provider = SEMANTIC_PROVIDER

    def _init_semantic(self):
        """Ленивая инициализация модели для семантического поиска."""
        if not self.semantic_initialized:
            if self.semantic_provider == "local":
                try:
                    self.semantic_model = SentenceTransformer(SEMANTIC_MODEL)
                    self.semantic_initialized = True
                    print(f"Локальная модель загружена: {SEMANTIC_MODEL}")
                except Exception as e:
                    print(f"Ошибка инициализации локальной модели: {e}")
                    self.semantic_initialized = False
            else:
                self.semantic_initialized = True
                print(f"Используется провайдер: {self.semantic_provider}")

    def match_keywords(self, text: str, keywords: Optional[str]) -> bool:
        """
        Проверка соответствия текста ключевым словам.

        Args:
            text: Текст для проверки
            keywords: Строка с ключевыми словами через запятую

        Returns:
            True если найдено хотя бы одно ключевое слово
        """
        if not keywords:
            return False

        text_lower = text.lower()
        keyword_list = [kw.strip().lower() for kw in keywords.split(",") if kw.strip()]

        for keyword in keyword_list:
            if keyword in text_lower:
                return True

        return False

    def match_semantic(self, text: str, topics: Optional[str], threshold: float = SEMANTIC_THRESHOLD) -> bool:
        """
        Проверка соответствия текста темам через семантический поиск.

        Args:
            text: Текст для проверки
            topics: Строка с темами через запятую
            threshold: Порог схожести (по умолчанию из конфига)

        Returns:
            True если найдена схожесть выше порога
        """
        if not topics:
            return False

        text_words = text.strip().split()
        text_length = len(text_words)
        
        if text_length == 1:
            adjusted_threshold = 0.85
        elif text_length == 2:
            adjusted_threshold = 0.35
        elif text_length == 3:
            adjusted_threshold = 0.35
        else:
            adjusted_threshold = 0.25

        self._init_semantic()

        topic_list = [t.strip() for t in topics.split(",") if t.strip()]
        if not topic_list:
            return False

        try:
            if self.semantic_provider == "local":
                return self._match_semantic_local(text, topic_list, adjusted_threshold, text_length)
            else:
                print(f"API провайдеры ({self.semantic_provider}) требуют async контекст")
                print(f"Используйте SEMANTIC_PROVIDER=local")
                return False
        except Exception as e:
            print(f"Ошибка семантического поиска: {e}")
            return False

    def _match_semantic_local(self, text: str, topic_list: List[str], threshold: float, text_length: int) -> bool:
        """Локальный семантический поиск через sentence-transformers с умной фильтрацией."""
        if not self.semantic_model:
            return False

        if text_length == 1:
            text_lower = text.lower().strip()
            topic_lower = topic_list[0].lower().strip() if topic_list else ""
            
            synonym_pairs = [
                ("deadline", "дедлайн"),
                ("дедлайн", "deadline"),
            ]
            
            for word1, word2 in synonym_pairs:
                if (text_lower == word1 and topic_lower == word2) or \
                   (text_lower == word2 and topic_lower == word1):
                    threshold = 0.55
                    break

        text_embedding = self.semantic_model.encode(text, convert_to_tensor=True)
        topic_embeddings = self.semantic_model.encode(topic_list, convert_to_tensor=True)
        similarities = cosine_similarity(text_embedding.unsqueeze(0), topic_embeddings)
        max_similarity = similarities.max().item()
        best_topic_idx = similarities.argmax().item()
        best_topic = topic_list[best_topic_idx] if best_topic_idx < len(topic_list) else topic_list[0]
        
        if max_similarity >= 0.50:
            false_positive_patterns = self._check_false_positive(text, best_topic)
            
            if false_positive_patterns:
                if text_length <= 3:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}, {text_length} слово(а)) - ЛОЖНОЕ СРАБАТЫВАНИЕ")
                else:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}) - ЛОЖНОЕ СРАБАТЫВАНИЕ")
                return False
            
            if text_length <= 3:
                print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}, {text_length} слово(а)) - ВЫСОКАЯ")
            else:
                print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}) - ВЫСОКАЯ")
            return max_similarity >= threshold
        
        if 0.35 <= max_similarity < 0.50:
            false_positive_patterns = self._check_false_positive(text, best_topic)
            
            if false_positive_patterns:
                if text_length <= 3:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}, {text_length} слово(а)) - ЛОЖНОЕ СРАБАТЫВАНИЕ")
                else:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}) - ЛОЖНОЕ СРАБАТЫВАНИЕ")
                return False
            
            if text_length == 1:
                return False
            
            topic_words = set(best_topic.lower().split())
            text_words = set(text.lower().split())
            topic_synonyms = self._get_topic_synonyms(best_topic)
            all_topic_words = topic_words | topic_synonyms
            common_words = all_topic_words & text_words
            has_common_words = len(common_words) > 0
            
            if has_common_words and max_similarity >= threshold:
                if text_length <= 3:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}, {text_length} слово(а)) - С ОБЩИМИ СЛОВАМИ")
                else:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}) - С ОБЩИМИ СЛОВАМИ")
                return True
            
            if max_similarity >= 0.45:
                if text_length <= 3:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}, {text_length} слово(а)) - ВЫСОКАЯ СХОЖЕСТЬ")
                else:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}) - ВЫСОКАЯ СХОЖЕСТЬ")
                return True
        
        if max_similarity < 0.35:
            if text_length == 1:
                return False
                
            topic_words = set(best_topic.lower().split())
            text_words = set(text.lower().split())
            common_words = topic_words & text_words
            
            if common_words and max_similarity >= threshold:
                if text_length <= 3:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}, {text_length} слово(а)) - С КЛЮЧЕВЫМИ СЛОВАМИ")
                else:
                    print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}) - С КЛЮЧЕВЫМИ СЛОВАМИ")
                return True
        
        if text_length <= 3:
            print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f}, {text_length} слово(а))")
        else:
            print(f"Схожесть: {max_similarity:.3f} (порог: {threshold:.3f})")
        return False
    
    def _check_false_positive(self, text: str, topic: str) -> bool:
        """Проверка на ложные срабатывания по известным паттернам."""
        text_lower = text.lower()
        topic_lower = topic.lower()
        
        false_positive_rules = {
            "дедлайн": {
                "forbidden": ["встреча", "купить", "погода", "привет", "продукты", "молоко", "программирование",
                             "готово", "готов", "сделано", "выполнено", "ок", "окей", "да", "нет", "спасибо"],
                "required": ["дедлайн", "deadline", "срок", "сдать", "сдачи", "крайний", "последний", "день"]
            },
            "программирование": {
                "forbidden": ["дедлайн", "встреча", "купить", "погода", "привет", "продукты", "молоко",
                             "готово", "готов", "сделано", "выполнено", "ок", "окей"],
                "required": ["программирование", "код", "разработка", "приложение", "python", "программа", "написать"]
            },
            "встреча": {
                "forbidden": ["дедлайн", "программирование", "купить", "погода", "продукты", "молоко",
                             "готово", "готов", "сделано", "выполнено"],
                "required": ["встреча", "собрание", "совещание", "встретимся"]
            },
        }
        
        if topic_lower in false_positive_rules:
            rules = false_positive_rules[topic_lower]
            forbidden_words = rules.get("forbidden", [])
            required_words = rules.get("required", [])
            
            has_forbidden = any(word in text_lower for word in forbidden_words)
            has_required = any(word in text_lower for word in required_words)
            
            if has_forbidden:
                main_topics = ["дедлайн", "программирование", "встреча"]
                for main_topic in main_topics:
                    if main_topic in forbidden_words and main_topic in text_lower:
                        if main_topic != topic_lower:
                            text_words = set(text_lower.split())
                            if main_topic in text_words:
                                return True
            
            if has_forbidden and not has_required:
                return True
        
        return False
    
    def _get_topic_synonyms(self, topic: str) -> set:
        """Получить набор синонимов для темы."""
        topic_lower = topic.lower()
        
        synonyms_dict = {
            "дедлайн": {"deadline", "срок", "сдачи", "крайний", "последний", "день", "сдать", "сдачи"},
            "программирование": {"код", "разработка", "приложение", "python", "программа", "написать"},
            "встреча": {"собрание", "совещание", "встретимся", "встречаемся"},
        }
        
        return synonyms_dict.get(topic_lower, set())

    async def _match_semantic_openrouter(self, text: str, topic_list: List[str], threshold: float, text_length: int) -> bool:
        """Семантический поиск через OpenRouter API (Qwen и др.)."""
        if not OPENROUTER_API_KEY:
            print("OPENROUTER_API_KEY не установлен")
            return False

        async with aiohttp.ClientSession() as session:
            prompt = f"""Определи, насколько текст "{text}" семантически близок к теме "{topic_list[0]}". 
Ответь только числом от 0.0 до 1.0, где 1.0 - полное совпадение, 0.0 - нет связи."""
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            
            try:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", 
                                      headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        similarity_text = result.get("choices", [{}])[0].get("message", {}).get("content", "0.0")
                        try:
                            similarity = float(similarity_text.strip())
                            print(f"         Схожесть (OpenRouter): {similarity:.3f} (порог: {threshold:.3f})")
                            return similarity >= threshold
                        except ValueError:
                            print(f"Не удалось распарсить ответ: {similarity_text}")
                            return False
                    else:
                        print(f"Ошибка OpenRouter API: {response.status}")
                        return False
            except Exception as e:
                print(f"Ошибка запроса к OpenRouter: {e}")
                return False

    async def _match_semantic_yandex(self, text: str, topic_list: List[str], threshold: float, text_length: int) -> bool:
        """Семантический поиск через YandexGPT API."""
        if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
            print("YANDEX_API_KEY или YANDEX_FOLDER_ID не установлены")
            return False

        async with aiohttp.ClientSession() as session:
            prompt = f"""Оцени семантическую близость текста "{text}" к теме "{topic_list[0]}". 
Ответь только числом от 0.0 до 1.0."""
            
            headers = {
                "Authorization": f"Api-Key {YANDEX_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.1
                },
                "messages": [{"role": "user", "text": prompt}]
            }
            
            try:
                async with session.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                                      headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        similarity_text = result.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "0.0")
                        try:
                            similarity = float(similarity_text.strip())
                            print(f"         Схожесть (YandexGPT): {similarity:.3f} (порог: {threshold:.3f})")
                            return similarity >= threshold
                        except ValueError:
                            return False
                    else:
                        return False
            except Exception as e:
                print(f"Ошибка YandexGPT: {e}")
                return False

    async def _match_semantic_openai(self, text: str, topic_list: List[str], threshold: float, text_length: int) -> bool:
        """Семантический поиск через OpenAI embeddings."""
        if not OPENAI_API_KEY:
            print("OPENAI_API_KEY не установлен")
            return False

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        try:
            text_emb = await client.embeddings.create(model=OPENAI_MODEL, input=text)
            topic_emb = await client.embeddings.create(model=OPENAI_MODEL, input=topic_list[0])
            
            import numpy as np
            text_vec = np.array(text_emb.data[0].embedding)
            topic_vec = np.array(topic_emb.data[0].embedding)
            
            similarity = np.dot(text_vec, topic_vec) / (np.linalg.norm(text_vec) * np.linalg.norm(topic_vec))
            
            print(f"         Схожесть (OpenAI): {similarity:.3f} (порог: {threshold:.3f})")
            return similarity >= threshold
        except Exception as e:
            print(f"Ошибка OpenAI: {e}")
            return False

    def should_forward(self, message_text: str, filters: List[dict]) -> bool:
        """
        Проверка, нужно ли пересылать сообщение на основе фильтров.

        Args:
            message_text: Текст сообщения
            filters: Список словарей с фильтрами (ключи: keywords, topics, use_semantic)

        Returns:
            True если сообщение соответствует хотя бы одному фильтру
        """
        if not message_text or not filters:
            return False

        for idx, filter_item in enumerate(filters):
            if filter_item.get("keywords"):
                keywords = filter_item["keywords"]
                if keywords and keywords.strip():
                    if self.match_keywords(message_text, keywords):
                        print(f"Сработал фильтр #{idx+1} (ключевые слова: '{keywords}')")
                        return True
                    else:
                        print(f"Фильтр #{idx+1} не сработал (ключевые слова: '{keywords}')")

            if filter_item.get("use_semantic") and filter_item.get("topics"):
                topics = filter_item["topics"]
                if topics and topics.strip():
                    if self.match_semantic(message_text, topics):
                        print(f"Сработал фильтр #{idx+1} (семантика: '{topics}')")
                        return True
                    else:
                        print(f"Фильтр #{idx+1} не сработал (семантика: '{topics}')")

        return False

