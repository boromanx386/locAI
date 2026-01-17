"""
Tools Handler for locAI.
Handles tool execution when model calls tools/function calling.
"""

import requests
from typing import Dict, Any, Optional
from urllib.parse import quote_plus
from datetime import datetime, timedelta

# Try to import ddgs for real web search
try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        # Fallback to old package name
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False


def get_available_tools() -> list:
    """
    Get list of available tools definitions for Ollama.
    
    Returns:
        List of tool definitions in Ollama format
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the internet for information about any topic. Use this tool when the user asks about current events, latest news, recent information, web search, online information, internet search, or any topic that requires up-to-date data. Also use for time queries (current time in different timezones), programming topics, AI models, technology news, or any information that might change over time. Always use this tool instead of relying on training data knowledge when the user asks about recent events, current information, or web content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to look up on the internet - what information to search for"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Dobija vremensku prognozu za dati grad. Koristi za informacije o vremenu.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "Ime grada za koji treba vremenska prognoza"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    ]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Execute a tool function and return result.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Arguments for the tool function
        
    Returns:
        Result string from tool execution
    """
    if tool_name == "search_web":
        return search_web(arguments.get("query", ""))
    elif tool_name == "get_weather":
        return get_weather(arguments.get("city", ""))
    else:
        return f"Tool '{tool_name}' nije implementiran."


def search_web(query: str) -> str:
    """
    Pretražuje internet koristeći DuckDuckGo API i worldtimeapi.org za vreme.
    
    Args:
        query: Search query
        
    Returns:
        Search results as string
    """
    print(f"[TOOL] Pretražujem web za: {query}")
    
    try:
        query_lower = query.lower()
        
        # Posebno rukovanje za vreme i datum - koristi worldtimeapi.org
        is_time_query = any(word in query_lower for word in ["vreme", "time", "date", "dan", "today", "danas"])
        
        if is_time_query:
            timezone = "Europe/Belgrade"  # Default
            if "beograd" in query_lower or "belgrade" in query_lower:
                timezone = "Europe/Belgrade"
            elif "london" in query_lower:
                timezone = "Europe/London"
            elif "new york" in query_lower:
                timezone = "America/New_York"
            elif "tokyo" in query_lower:
                timezone = "Asia/Tokyo"
            elif "paris" in query_lower:
                timezone = "Europe/Paris"
            elif "berlin" in query_lower:
                timezone = "Europe/Berlin"
            elif "zagreb" in query_lower:
                timezone = "Europe/Zagreb"
            elif "ljubljana" in query_lower:
                timezone = "Europe/Ljubljana"
            
            try:
                # Koristim HTTPS
                time_url = f"https://worldtimeapi.org/api/timezone/{timezone}"
                time_response = requests.get(time_url, timeout=5, verify=True)
                if time_response.status_code == 200:
                    time_data = time_response.json()
                    current_time = time_data.get("datetime", "")
                    timezone_abbr = time_data.get("abbreviation", "")
                    if current_time:
                        # Formatiraj vreme i datum
                        dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
                        
                        # Proveri da li traže samo datum ili i vreme
                        if "date" in query_lower or "dan" in query_lower or ("today" in query_lower and "time" not in query_lower):
                            # Samo datum
                            formatted_date = dt.strftime("%Y-%m-%d")
                            day_name = dt.strftime("%A")
                            city_name = timezone.split('/')[-1].replace('_', ' ')
                            return f"Danas u {city_name} ({timezone_abbr}): {formatted_date}, {day_name}"
                        else:
                            # Datum i vreme
                            formatted_datetime = dt.strftime("%Y-%m-%d %H:%M:%S")
                            day_name = dt.strftime("%A")
                            city_name = timezone.split('/')[-1].replace('_', ' ')
                            return f"Trenutno vreme u {city_name} ({timezone_abbr}): {formatted_datetime}, {day_name}"
            except Exception as e:
                print(f"[GREŠKA] Error pri dobijanju vremena: {e}")
                # Fallback na lokalno vreme
                now = datetime.now()
                if "date" in query_lower or "dan" in query_lower:
                    local_date = now.strftime("%Y-%m-%d")
                    day_name = now.strftime("%A")
                    return f"Danas (lokalno): {local_date}, {day_name}"
                else:
                    local_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    day_name = now.strftime("%A")
                    return f"Trenutno vreme (lokalno): {local_time}, {day_name}"
        
        # Za ostalo - DuckDuckGo Instant Answer API (stvarno pretražuje!)
        ia_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        ia_response = requests.get(ia_url, timeout=10, headers=headers)
        
        if ia_response.status_code == 200:
            ia_data = ia_response.json()
            
            # AbstractText (kratak odgovor) - STVARNO sa interneta!
            if ia_data.get("AbstractText"):
                result = ia_data["AbstractText"]
                if ia_data.get("AbstractURL"):
                    result += f"\nIzvor: {ia_data['AbstractURL']}"
                return result
            
            # Answer (kratak odgovor) - STVARNO sa interneta!
            if ia_data.get("Answer"):
                return ia_data["Answer"]
            
            # RelatedTopics (srodne teme) - STVARNO sa interneta!
            if ia_data.get("RelatedTopics") and len(ia_data["RelatedTopics"]) > 0:
                topics = ia_data["RelatedTopics"][:5]  # Prva 5 rezultata
                results = []
                for topic in topics:
                    if isinstance(topic, dict) and "Text" in topic:
                        text = topic["Text"]
                        # Limitaj na 300 karaktera po rezultatu
                        if len(text) > 300:
                            text = text[:300] + "..."
                        results.append(text)
                    elif isinstance(topic, dict) and "FirstURL" in topic:
                        # Neki rezultati imaju samo URL
                        results.append(f"{topic.get('Text', topic['FirstURL'])} - {topic['FirstURL']}")
                if results:
                    return "\n\n".join(results)
        
        # DuckDuckGo Instant Answer API vraća prazan rezultat za neke upite
        # Fallback na DuckDuckGo HTML search (STVARNA PRETRAGA!)
        if HAS_DDGS:
            try:
                print(f"[TOOL] Instant Answer API nije našao rezultate, pokušavam HTML pretragu...")
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=10))
                    if results:
                        search_results = []
                        for r in results:
                            title = r.get("title", "").strip()
                            body = r.get("body", "").strip()
                            href = r.get("href", "").strip()
                            
                            # Filtriraj loše rezultate
                            if not body or len(body) < 20:
                                continue
                            
                            # Preskoči ako je samo "opens in a new window" ili slično
                            if any(skip in body.lower()[:50] for skip in ["opens in a new", "click here", "read more"]):
                                continue
                            
                            # Skrati body ako je predugačak
                            if len(body) > 400:
                                body = body[:400] + "..."
                            
                            if title and body and href:
                                search_results.append(f"{title}\n{body}\n{href}")
                        
                        if search_results:
                            # Vrati prvih 7 najboljih rezultata
                            return "\n\n---\n\n".join(search_results[:7])
            except Exception as e:
                print(f"[GREŠKA] Error u DuckDuckGo HTML pretrazi: {e}")
        
        return f"Nisam pronašao rezultate za '{query}'. Pokušajte sa drugačijim upitom."
        
    except requests.exceptions.Timeout:
        return f"Zahtev je istekao za pretragu '{query}'."
    except requests.exceptions.ConnectionError:
        return f"Nema internet konekcije za pretragu '{query}'."
    except Exception as e:
        print(f"[GREŠKA] Error u search_web: {e}")
        return f"Greška pri pretrazi '{query}': {str(e)}"


def get_weather(city: str) -> str:
    """
    Dobija vremensku prognozu za dati grad.
    Koristi wttr.in API (besplatan, bez API key-a).
    
    Args:
        city: Ime grada
        
    Returns:
        Vremenska prognoza kao string
    """
    print(f"[TOOL] Dobijam vremensku prognozu za: {city}")
    
    try:
        # wttr.in je besplatan weather API bez potrebe za API key
        # Formatiraj ime grada za URL (zameni razmake sa +)
        city_formatted = quote_plus(city)
        weather_url = f"https://wttr.in/{city_formatted}?format=j1"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        weather_response = requests.get(weather_url, timeout=10, headers=headers)
        
        if weather_response.status_code == 200:
            weather_data = weather_response.json()
            
            # Parsuj JSON odgovor
            current = weather_data.get("current_condition", [{}])[0]
            forecast = weather_data.get("weather", [])
            
            # Trenutno vreme
            temp_c = current.get("temp_C", "N/A")
            feels_like = current.get("FeelsLikeC", "N/A")
            desc = current.get("weatherDesc", [{}])[0].get("value", "N/A")
            humidity = current.get("humidity", "N/A")
            wind_kmh = current.get("windspeedKmph", "N/A")
            
            result = f"Vremenska prognoza za {city}:\n"
            result += f"Trenutno: {temp_c}°C (oseća se kao {feels_like}°C), {desc}\n"
            result += f"Vlažnost: {humidity}%, Vetar: {wind_kmh} km/h\n\n"
            
            # Prognoza za sledeća 3 dana
            if forecast:
                result += "Prognoza:\n"
                for day in forecast[:3]:
                    date = day.get("date", "")
                    max_temp = day.get("maxtempC", "N/A")
                    min_temp = day.get("mintempC", "N/A")
                    daily_desc = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "N/A")
                    
                    # Formatiraj datum
                    if date:
                        try:
                            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                            today = datetime.now().date()
                            tomorrow = today + timedelta(days=1)
                            
                            if date_obj == today:
                                date_str = "Danas"
                            elif date_obj == tomorrow:
                                date_str = "Sutra"
                            else:
                                date_str = date_obj.strftime("%d.%m")
                        except:
                            date_str = date
                    else:
                        date_str = "N/A"
                    
                    result += f"- {date_str}: {min_temp}°C - {max_temp}°C, {daily_desc}\n"
            
            return result.strip()
        else:
            return f"Nisam mogao da dobijem vremensku prognozu za {city}. Status code: {weather_response.status_code}"
            
    except requests.exceptions.Timeout:
        return f"Zahtev za vremensku prognozu je istekao za {city}."
    except requests.exceptions.ConnectionError:
        return f"Nema internet konekcije za vremensku prognozu za {city}."
    except Exception as e:
        print(f"[GREŠKA] Error u get_weather: {e}")
        # Fallback na simulirane podatke samo ako je poznat grad
        city_lower = city.lower()
        if city_lower in ["beograd", "belgrade"]:
            return f"Vremenska prognoza za Beograd (fallback):\n- Danas: 15°C, oblačno\n- Sutra: 18°C, sunčano\n- Prekosutra: 16°C, kiša\n\n[Greška pri dobijanju stvarne prognoze: {str(e)}]"
        return f"Greška pri dobijanju vremenske prognoze za {city}: {str(e)}"
