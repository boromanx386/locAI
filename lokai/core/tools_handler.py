"""
Tools Handler for locAI.
Handles tool execution when model calls tools/function calling.
"""

import requests
from typing import Dict, Any, Optional, TYPE_CHECKING
from urllib.parse import quote_plus, urlparse
from datetime import datetime, timedelta
import socket
import ipaddress

if TYPE_CHECKING:
    from lokai.core.config_manager import ConfigManager

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

# Try to import yt-dlp for YouTube
try:
    from yt_dlp import YoutubeDL
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

# Try to import deep-translator for translation
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

# Try to import BeautifulSoup4 for web scraping
try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False

# Try to import youtube-transcript-api for YouTube transcripts
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YOUTUBE_TRANSCRIPT = True
except ImportError:
    HAS_YOUTUBE_TRANSCRIPT = False

import json
import math
import re

# Tools that are not executed immediately - they run after LLM finishes and models unload
DEFERRED_TOOLS = {"generate_image", "generate_audio"}


def _is_private_or_disallowed_url(url: str) -> bool:
    """
    Return True if the URL is not allowed for security reasons (SSRF protection).

    Rules:
    - Only http/https schemes are allowed.
    - Block localhost / loopback / link-local / private IP ranges.
    """
    try:
        parsed = urlparse(url)

        # Require explicit http/https scheme
        if parsed.scheme not in ("http", "https"):
            return True

        host = parsed.hostname or ""
        if not host:
            return True

        # Explicit hostnames to block
        if host.lower() in ("localhost",):
            return True

        # Resolve host and check all IPs
        try:
            addr_infos = socket.getaddrinfo(host, None)
        except Exception:
            # If we cannot resolve, be conservative and block
            return True

        for family, _, _, _, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                # Skip weird results, but continue checking others
                continue

            if ip.is_loopback or ip.is_private or ip.is_link_local:
                return True

        # All resolved IPs are public
        return False
    except Exception:
        # On any parsing error, block to be safe
        return True


def get_available_tools(config_manager: Optional["ConfigManager"] = None) -> list:
    """
    Get list of available tools definitions for Ollama.
    
    Args:
        config_manager: Optional ConfigManager instance to check tool toggle settings.
                       If None, all tools are enabled by default.
    
    Returns:
        List of tool definitions in Ollama format
    """
    tools = []
    
    # Helper function to check if tool is enabled
    def is_tool_enabled(tool_name: str, default: bool = True) -> bool:
        if config_manager is None:
            return default
        return config_manager.get(f"ollama.tools.{tool_name}", default)
    
    # search_web - always enabled if tools are enabled
    tools.append({
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
    })
    
    # get_weather - check toggle
    if is_tool_enabled("weather", True):
        tools.append({
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Gets weather forecast for a given city. Use this tool when the user asks about weather, temperature, forecast, or current weather conditions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "Name of the city for weather forecast"
                        }
                    },
                    "required": ["city"]
                }
            }
        })
    
    # Other tools (always enabled by default)
    tools.extend([
        {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Searches for code on GitHub. Use this tool to find code examples, implementations, analyze public repositories. Can search for specific files, functions, classes in GitHub repositories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in code (e.g. 'function calculate', 'class MainWindow', 'React hooks')"
                        },
                        "repo": {
                            "type": "string",
                            "description": "GitHub repository in format 'owner/repo' (e.g. 'microsoft/vscode') or GitHub URL. If not specified, searches all public repositories."
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to specific file in repository (e.g. 'src/main.py'). Optional."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "translate",
                "description": "Translates text from one language to another. Use this tool to translate any text or sentences between different languages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to translate"
                        },
                        "target_language": {
                            "type": "string",
                            "description": "Target language to translate to (e.g. 'sr', 'en', 'de', 'fr', 'es'). If not specified, automatically detects and translates to English."
                        },
                        "source_language": {
                            "type": "string",
                            "description": "Source language of the text (e.g. 'sr', 'en'). If not specified, automatically detects."
                        }
                    },
                    "required": ["text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_youtube",
                "description": "Searches YouTube videos or gets information about a specific video. Can get metadata (title, description, channel, duration), transcript (if available), and search videos by query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for videos (e.g. 'Python tutorial', 'AI models 2024'). If not specified, uses video_url."
                        },
                        "video_url": {
                            "type": "string",
                            "description": "YouTube video URL (e.g. 'https://www.youtube.com/watch?v=...') to get video details."
                        },
                        "get_transcript": {
                            "type": "boolean",
                            "description": "Whether to fetch video transcript (if video_url is specified). Default: false."
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of search results. Default: 5."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fact_check",
                "description": "Verifies the truthfulness of information or claims by searching the internet and comparing with reliable sources. Use this tool to verify facts, statistics, news, or any information that needs to be checked.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "Claim or information to verify (e.g. 'Python is the most popular programming language', 'Current time in Belgrade is 15:00')"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Optional topic or keyword to focus the search (e.g. 'programming languages', 'current time Belgrade')"
                        }
                    },
                    "required": ["claim"]
                }
            }
        },
    ])
    
    # open_url - fetch page content from URL (models often expect this)
    tools.append({
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Fetch and return text content from a URL. Use when you need to read a specific webpage, documentation, Hugging Face model page, GitHub README, or article. Returns the main text content of the page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch (e.g. https://huggingface.co/nvidia/personaplex-7b-v1)"
                    }
                },
                "required": ["url"]
            }
        }
    })
    
    # scrape_webpage - check toggle (default: false to avoid slowdowns)
    if is_tool_enabled("scrape_webpage", False):
        tools.append(
        {
            "type": "function",
            "function": {
                "name": "scrape_webpage",
                "description": "Parses HTML content of a web page and extracts specific data. Use this tool when the user requests specific information from a web page - e.g. extract all links, tables, lists, headings, paragraphs, or other HTML elements from a given URL. Also use when search_web returns a relevant URL and you need to extract detailed information directly from that page. Use only with public, accessible web pages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the web page to parse (e.g. 'https://example.com/page')"
                        },
                        "extract": {
                            "type": "string",
                            "description": "What to extract from the page: 'links' (all links), 'tables' (tables), 'text' (all text), 'headings' (h1-h6 headings), 'images' (images), 'lists' (ul/ol lists), 'all' (all elements). Default: 'text'",
                            "enum": ["links", "tables", "text", "headings", "images", "lists", "all"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of elements to extract (e.g. first 10 links). Default: 50"
                        }
                    },
                    "required": ["url"]
                }
            }
        }
    )

    # generate_image - deferred (runs after LLM unloads)
    if is_tool_enabled("generate_image", True):
        tools.append({
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": "Generate an image from a text description. Use when user asks to create, draw, or generate an image, picture, illustration, or artwork. Always write the prompt in English. Keep the prompt concise: 2-3 sentences maximum.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Description of the image to generate. Must be in English - translate from user's language if needed. Maximum 2-3 sentences - keep it concise for best results."
                        }
                    },
                    "required": ["prompt"]
                }
            }
        })

    # generate_audio - deferred (runs after LLM unloads)
    # Uses Stable Audio - generates SOUNDS/MUSIC from description, NOT text-to-speech
    if is_tool_enabled("generate_audio", True):
        tools.append({
            "type": "function",
            "function": {
                "name": "generate_audio",
                "description": "Generate sounds or music from a text description. Use when user asks for music, instrument sounds, sound effects, beats, ambient audio, etc. This is NOT text-to-speech - it generates audio like drum beats, piano melodies, electronic music from a descriptive prompt. Always provide the prompt in English.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Description of the audio to generate (e.g. 'heavy bass drum beat', 'piano melody', 'ambient electronic music'). Must be in English - translate from user's language if needed. This describes the SOUND to create, not text to speak."
                        }
                    },
                    "required": ["text"]
                }
            }
        })

    return tools


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
    elif tool_name == "search_code":
        return search_code(
            arguments.get("query", ""),
            arguments.get("repo"),
            arguments.get("file_path")
        )
    elif tool_name == "translate":
        return translate(
            arguments.get("text", ""),
            arguments.get("target_language", "en"),
            arguments.get("source_language")
        )
    elif tool_name == "search_youtube":
        return search_youtube(
            arguments.get("query"),
            arguments.get("video_url"),
            arguments.get("get_transcript", False),
            arguments.get("max_results", 5)
        )
    elif tool_name == "fact_check":
        return fact_check(
            arguments.get("claim", ""),
            arguments.get("topic")
        )
    elif tool_name == "scrape_webpage":
        return scrape_webpage(
            arguments.get("url", ""),
            arguments.get("extract", "text"),
            arguments.get("limit", 50)
        )
    elif tool_name == "open_url":
        return scrape_webpage(
            arguments.get("url", ""),
            "text",
            50
        )
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
        current_year = datetime.now().year
        
        # Uvek proveri i popravi stare godine u query-ju
        year_pattern = r'\b(20\d{2})\b'
        years_found = re.findall(year_pattern, query)
        
        if years_found:
            # Pronađi najveću godinu u query-ju
            max_year_found = max(int(y) for y in years_found)
            # Ako je godina starija od trenutne, zameni je
            if max_year_found < current_year:
                print(f"[TOOL] Pronađena stara godina {max_year_found} u query-ju, zamenjujem sa {current_year}")
                # Zameni sve stare godine trenutnom
                query = re.sub(year_pattern, str(current_year), query)
                query_lower = query.lower()
        
        # Za vesti/novosti/tehničke upite - dodaj godinu ako nema
        is_time_sensitive_query = any(word in query_lower for word in [
            "news", "vesti", "novosti", "latest", "recent", "current", "today", "danas",
            "best", "top", "new", "modern", "updated", "current", "2024", "2025"
        ])
        
        if is_time_sensitive_query and not years_found:
            # Ako je upit vezan za trenutne/novije informacije a nema godine, dodaj trenutnu
            print(f"[TOOL] Dodajem trenutnu godinu {current_year} u time-sensitive query")
            query = f"{query} {current_year}"
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
                            return f"Today in {city_name} ({timezone_abbr}): {formatted_date}, {day_name}"
                        else:
                            # Datum i vreme
                            formatted_datetime = dt.strftime("%Y-%m-%d %H:%M:%S")
                            day_name = dt.strftime("%A")
                            city_name = timezone.split('/')[-1].replace('_', ' ')
                            return f"Current time in {city_name} ({timezone_abbr}): {formatted_datetime}, {day_name}"
            except Exception as e:
                print(f"[GREŠKA] Error pri dobijanju vremena: {e}")
                # Fallback na lokalno vreme
                now = datetime.now()
                if "date" in query_lower or "dan" in query_lower:
                    local_date = now.strftime("%Y-%m-%d")
                    day_name = now.strftime("%A")
                    return f"Today (local): {local_date}, {day_name}"
                else:
                    local_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    day_name = now.strftime("%A")
                    return f"Current time (local): {local_time}, {day_name}"
        
        # Za ostalo - DuckDuckGo Instant Answer API (stvarno pretražuje!)
        ia_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        ia_response = requests.get(ia_url, timeout=10, headers=headers)
        
        ia_data = None
        if ia_response.status_code == 200 and ia_response.text and ia_response.text.strip():
            try:
                ia_data = ia_response.json()
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[TOOL] Instant Answer API vratio nevalidan JSON: {e}")
                ia_data = None
        
        if ia_data:
            # AbstractText (kratak odgovor) - STVARNO sa interneta!
            if ia_data.get("AbstractText"):
                result = ia_data["AbstractText"]
                if ia_data.get("AbstractURL"):
                    result += f"\nSource: {ia_data['AbstractURL']}"
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
        
        # DuckDuckGo Instant Answer API vraća prazan/nevalidan rezultat za neke upite
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
        
        return f"No results found for '{query}'. Try a different query."
        
    except requests.exceptions.Timeout:
        return f"Request timed out for search '{query}'."
    except requests.exceptions.ConnectionError:
        return f"No internet connection for search '{query}'."
    except Exception as e:
        print(f"[GREŠKA] Error u search_web: {e}")
        return f"Error searching '{query}': {str(e)}"


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
            
            result = f"Weather forecast for {city}:\n"
            result += f"Current: {temp_c}°C (feels like {feels_like}°C), {desc}\n"
            result += f"Humidity: {humidity}%, Wind: {wind_kmh} km/h\n\n"
            
            # Prognoza za sledeća 3 dana
            if forecast:
                result += "Forecast:\n"
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
                                date_str = "Today"
                            elif date_obj == tomorrow:
                                date_str = "Tomorrow"
                            else:
                                date_str = date_obj.strftime("%m/%d")
                        except:
                            date_str = date
                    else:
                        date_str = "N/A"
                    
                    result += f"- {date_str}: {min_temp}°C - {max_temp}°C, {daily_desc}\n"
            
            return result.strip()
        else:
            return f"Could not get weather forecast for {city}. Status code: {weather_response.status_code}"
            
    except requests.exceptions.Timeout:
        return f"Weather forecast request timed out for {city}."
    except requests.exceptions.ConnectionError:
        return f"No internet connection for weather forecast for {city}."
    except Exception as e:
        print(f"[GREŠKA] Error u get_weather: {e}")
        # Fallback na simulirane podatke samo ako je poznat grad
        city_lower = city.lower()
        if city_lower in ["beograd", "belgrade"]:
            return f"Weather forecast for Belgrade (fallback):\n- Today: 15°C, cloudy\n- Tomorrow: 18°C, sunny\n- Day after: 16°C, rain\n\n[Error getting real forecast: {str(e)}]"
        return f"Error getting weather forecast for {city}: {str(e)}"


def search_code(query: str, repo: Optional[str] = None, file_path: Optional[str] = None) -> str:
    """
    Pretražuje kod na GitHub-u.
    
    Args:
        query: Šta tražiš u kodu
        repo: GitHub repo u formatu 'owner/repo' ili URL
        file_path: Putanja do konkretnog fajla
        
    Returns:
        Rezultati pretrage ili sadržaj fajla
    """
    print(f"[TOOL] Pretražujem kod za: {query}, repo: {repo}, file: {file_path}")
    
    try:
        # Ako je naveden konkretan fajl, preuzmi direktno sa GitHub-a
        if repo and file_path:
            # Parsuj repo iz URL-a ili owner/repo formata
            if "github.com" in repo:
                # Izvuci owner/repo iz URL-a
                match = re.search(r"github\.com/([^/]+)/([^/]+)", repo)
                if match:
                    owner, repo_name = match.groups()
                    repo = f"{owner}/{repo_name}"
            elif "/" not in repo:
                return f"Error: Invalid repo format. Use 'owner/repo' or GitHub URL."
            
            # Preuzmi fajl direktno sa GitHub-a (raw content API)
            # Pokušaj sa main, master, ili HEAD branch-om
            for branch in ["main", "master", "HEAD"]:
                try:
                    file_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
                    response = requests.get(file_url, timeout=10)
                    if response.status_code == 200:
                        content = response.text
                        # Limitaj veličinu (max 5000 linija)
                        lines = content.split('\n')
                        if len(lines) > 5000:
                            content = '\n'.join(lines[:5000]) + f"\n\n[... {len(lines) - 5000} lines remaining ...]"
                        return f"File content {file_path} from {repo}:\n\n{content}"
                except:
                    continue
            
            return f"File {file_path} not found in repository {repo}"
        
        # Ako nije naveden konkretan fajl, pretražuj DuckDuckGo za GitHub rezultate
        search_query = f"site:github.com {query}"
        if repo:
            search_query += f" {repo}"
        
        if HAS_DDGS:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(search_query, max_results=10))
                    if results:
                        github_results = []
                        for r in results:
                            url = r.get("href", "")
                            if "github.com" in url and ("blob" in url or "tree" in url):
                                title = r.get("title", "")
                                body = r.get("body", "")[:300]
                                github_results.append(f"{title}\n{body}\n{url}")
                        
                        if github_results:
                            return "\n\n---\n\n".join(github_results[:7])
            except Exception as e:
                print(f"[GREŠKA] Error u GitHub pretrazi: {e}")
        
        # Fallback: vrati opštu pretragu
        return f"Searched GitHub for '{query}'. Results:\n\nNo specific code found. Try specifying repo and file path."
        
    except Exception as e:
        print(f"[GREŠKA] Error u search_code: {e}")
        return f"Error searching code: {str(e)}"


def translate(text: str, target_language: str = "en", source_language: Optional[str] = None) -> str:
    """
    Prevodi tekst sa jednog jezika na drugi.
    
    Args:
        text: Tekst za prevod
        target_language: Jezik na koji prevodi (sr, en, de, fr, es, it, ru, ja, zh, itd.)
        source_language: Izvorni jezik (opciono, automatski detektuje ako nije naveden)
        
    Returns:
        Prevedeni tekst
    """
    print(f"[TOOL] Prevodi tekst: '{text[:50]}...' -> {target_language}")
    
    if not text or not text.strip():
        return "Error: Text to translate is empty."
    
    if HAS_TRANSLATOR:
        try:
            translator = GoogleTranslator(source=source_language or 'auto', target=target_language)
            translated = translator.translate(text)
            return translated
        except Exception as e:
            print(f"[GREŠKA] Error u translate: {e}")
            return f"Error translating: {str(e)}"
    else:
        return "Translation not available - missing library 'deep-translator'. Install: pip install deep-translator"


def search_youtube(query: Optional[str] = None, video_url: Optional[str] = None,
                   get_transcript: bool = False, max_results: int = 5) -> str:
    """
    Pretražuje YouTube videozapise ili dobija info o videu.
    
    Args:
        query: Pretraga videozapisa
        video_url: YouTube URL za konkretan video
        get_transcript: Da li da preuzme transkript
        max_results: Maksimalan broj rezultata
        
    Returns:
        Rezultati pretrage ili info o videu
    """
    print(f"[TOOL] YouTube: query={query}, url={video_url}, transcript={get_transcript}")
    
    try:
        # Ako je naveden konkretan video URL, dobij info o videu
        if video_url:
            if HAS_YTDLP:
                try:
                    ydl_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'skip_download': True,
                    }
                    
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(video_url, download=False)
                        
                        result = f"YouTube Video:\n"
                        result += f"Title: {info.get('title', 'N/A')}\n"
                        result += f"Channel: {info.get('uploader', 'N/A')}\n"
                        duration = info.get('duration', 0)
                        if duration:
                            minutes = duration // 60
                            seconds = duration % 60
                            result += f"Duration: {minutes}:{seconds:02d}\n"
                        result += f"Views: {info.get('view_count', 0):,}\n"
                        result += f"Upload date: {info.get('upload_date', 'N/A')}\n"
                        desc = info.get('description', '')
                        if desc:
                            # Limitaj opis na 500 karaktera
                            if len(desc) > 500:
                                desc = desc[:500] + "..."
                            result += f"\nDescription:\n{desc}\n"
                        
                        result += f"\nURL: {video_url}\n"
                        
                        # Ako traži transkript - koristi youtube-transcript-api
                        if get_transcript:
                            try:
                                # Izvuci video ID iz URL-a
                                video_id = None
                                if "watch?v=" in video_url:
                                    video_id = video_url.split("watch?v=")[1].split("&")[0]
                                elif "youtu.be/" in video_url:
                                    video_id = video_url.split("youtu.be/")[1].split("?")[0]
                                
                                if video_id and HAS_YOUTUBE_TRANSCRIPT:
                                    print(f"[TOOL] Preuzimam transkript za video ID: {video_id}")
                                    try:
                                        # Napravi instancu i pozovi fetch
                                        api = YouTubeTranscriptApi()
                                        transcript = api.fetch(video_id, languages=['en'])
                                        
                                        # Spoji sve segmente u jedan tekst
                                        transcript_text = " ".join([item.text for item in transcript])
                                        print(f"[TOOL] Transkript uspešno preuzet, dužina: {len(transcript_text)} karaktera")
                                        result += f"\n\n--- Transcript ---\n{transcript_text}\n"
                                    except Exception as transcript_error:
                                        print(f"[TOOL] Greška pri preuzimanju transkripta: {transcript_error}")
                                        # Pokušaj sa drugim jezicima ili bilo kojim dostupnim
                                        try:
                                            api = YouTubeTranscriptApi()
                                            transcript_list = api.list(video_id)
                                            # Pokušaj prvo sa engleskim
                                            transcript = transcript_list.find_transcript(['en'])
                                            transcript_data = transcript.fetch()
                                            transcript_text = " ".join([item.text for item in transcript_data])
                                            print(f"[TOOL] Transkript preuzet (engleski), dužina: {len(transcript_text)} karaktera")
                                            result += f"\n\n--- Transcript (English) ---\n{transcript_text}\n"
                                        except Exception as e2:
                                            # Pokušaj sa bilo kojim dostupnim jezikom
                                            try:
                                                api = YouTubeTranscriptApi()
                                                transcript_list = api.list(video_id)
                                                # Pokušaj prvo sa manually created, pa sa generated
                                                try:
                                                    transcript = transcript_list.find_manually_created_transcript(['en'])
                                                except:
                                                    transcript = transcript_list.find_generated_transcript(['en'])
                                                
                                                transcript_data = transcript.fetch()
                                                transcript_text = " ".join([item.text for item in transcript_data])
                                                print(f"[TOOL] Transkript preuzet (alternativni način), dužina: {len(transcript_text)} karaktera")
                                                result += f"\n\n--- Transcript ---\n{transcript_text}\n"
                                            except Exception as e3:
                                                print(f"[TOOL] Svi pokušaji neuspešni. Greške: {transcript_error}, {e2}, {e3}")
                                                result += f"\n\n[Transcript] Transcript not available for this video. Error: {str(transcript_error)}"
                                elif video_id and not HAS_YOUTUBE_TRANSCRIPT:
                                    print(f"[TOOL] youtube-transcript-api biblioteka nije instalirana!")
                                    result += "\n\n[Transcript] Transcript downloading requires 'youtube-transcript-api' library. Install: pip install youtube-transcript-api"
                                else:
                                    print(f"[TOOL] Video ID nije izvučen iz URL-a: {video_url}")
                                    result += "\n\n[Transcript] Could not extract video ID from URL."
                            except Exception as e:
                                print(f"[GREŠKA] Error pri preuzimanju transkripta: {e}")
                                import traceback
                                traceback.print_exc()
                                result += f"\n\n[Transcript] Error fetching transcript: {str(e)}"
                        
                        return result
                except Exception as e:
                    print(f"[GREŠKA] Error pri preuzimanju YouTube info: {e}")
                    return f"Error fetching video information: {str(e)}"
            else:
                return "YouTube search not available - missing library 'yt-dlp'. Install: pip install yt-dlp"
        
        # Pretraga videozapisa
        if query:
            # Koristi DuckDuckGo za pretragu YouTube linkova
            search_query = f"site:youtube.com {query}"
            
            if HAS_DDGS:
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(search_query, max_results=max_results))
                        if results:
                            youtube_results = []
                            for r in results:
                                url = r.get("href", "")
                                if "youtube.com" in url or "youtu.be" in url:
                                    title = r.get("title", "")
                                    body = r.get("body", "")[:200]
                                    youtube_results.append(f"{title}\n{body}\n{url}")
                            
                            if youtube_results:
                                return "YouTube search:\n\n" + "\n\n---\n\n".join(youtube_results)
                except Exception as e:
                    print(f"[GREŠKA] Error u YouTube pretrazi: {e}")
            
            return f"No YouTube videos found for '{query}'."
        
        return "Error: Neither query nor video_url specified."
        
    except Exception as e:
        print(f"[GREŠKA] Error u search_youtube: {e}")
        return f"Error in YouTube search: {str(e)}"


def fact_check(claim: str, topic: Optional[str] = None) -> str:
    """
    Proverava istinitost informacije pretragom interneta.
    
    Args:
        claim: Tvrdnja ili informacija za proveru
        topic: Opciona tema za fokusiranje pretrage
        
    Returns:
        Rezultati provere činjenica
    """
    print(f"[TOOL] Proveravam činjenicu: {claim[:100]}...")
    
    try:
        # Formiraj pretragu za fakt-cheking
        search_query = claim
        if topic:
            search_query = f"{topic} {claim}"
        
        # Dodaj ključne reči za fakt-cheking
        fact_check_query = f"fact check {search_query} verification"
        
        # Koristi search_web za pretragu
        if HAS_DDGS:
            try:
                with DDGS() as ddgs:
                    # Prvo pretraga za fakt-cheking
                    results = list(ddgs.text(fact_check_query, max_results=5))
                    
                    # Takođe regular pretraga
                    regular_results = list(ddgs.text(search_query, max_results=5))
                    
                    fact_check_sources = []
                    regular_sources = []
                    
                    # Parsuj fakt-checking rezultate
                    for r in results:
                        url = r.get("href", "")
                        title = r.get("title", "").lower()
                        # Fakt-cheking sajtovi
                        if any(site in url.lower() for site in ["snopes.com", "factcheck.org", "politifact.com", "reuters.com", "bbc.com", "apnews.com"]):
                            fact_check_sources.append({
                                "title": r.get("title", ""),
                                "body": r.get("body", "")[:300],
                                "url": url
                            })
                    
                    # Parsuj regularne rezultate
                    for r in regular_results[:5]:
                        regular_sources.append({
                            "title": r.get("title", ""),
                            "body": r.get("body", "")[:300],
                            "url": r.get("href", "")
                        })
                    
                    result = f"Fact check for: '{claim}'\n\n"
                    
                    if fact_check_sources:
                        result += "Fact-checking sources:\n"
                        for i, source in enumerate(fact_check_sources[:3], 1):
                            result += f"\n{i}. {source['title']}\n{source['body']}\n{source['url']}\n"
                        result += "\n"
                    
                    if regular_sources:
                        result += "Relevant sources:\n"
                        for i, source in enumerate(regular_sources[:3], 1):
                            result += f"\n{i}. {source['title']}\n{source['body']}\n{source['url']}\n"
                    
                    if not fact_check_sources and not regular_sources:
                        result += "No specific fact-checking sources found. Recommend manual verification."
                    
                    return result
            except Exception as e:
                print(f"[GREŠKA] Error u fact_check pretrazi: {e}")
        
        # Fallback: koristi običnu pretragu
        return search_web(claim)
        
    except Exception as e:
        print(f"[GREŠKA] Error u fact_check: {e}")
        return f"Error fact-checking: {str(e)}"


def scrape_webpage(url: str, extract: str = "text", limit: int = 50) -> str:
    """
    Parsira HTML web stranice i izvlači podatke koristeći BeautifulSoup4.
    
    Args:
        url: URL adresa web stranice
        extract: Šta izvući (links, tables, text, headings, images, lists, all)
        limit: Maksimalan broj elemenata za izvlačenje
        
    Returns:
        Izvučeni podaci kao string
    """
    print(f"[TOOL] Parsiram web stranicu: {url}, extract: {extract}, limit: {limit}")

    # Basic validation and SSRF protection
    if not url:
        return "Error: URL is required."
    if _is_private_or_disallowed_url(url):
        return (
            "Error: This URL is not allowed for security reasons. "
            "Only public http/https URLs are supported."
        )

    if not HAS_BEAUTIFULSOUP:
        return "Web scraping not available - missing library 'beautifulsoup4'. Install: pip install beautifulsoup4"
    
    try:
        # Preuzmi HTML stranice
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, timeout=10, headers=headers)
        
        if response.status_code != 200:
            return f"Error: Cannot access page {url} (status code: {response.status_code})"
        
        # Parsiraj HTML sa BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ukloni script, style i komentare za čišći tekst
        for element in soup(["script", "style", "meta", "link", "noscript"]):
            element.decompose()
        
        result = f"Content from {url}:\n\n"
        
        if extract == "links" or extract == "all":
            links = soup.find_all('a', href=True)
            if links:
                link_results = []
                for link in links[:limit]:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    # Konvertuj relativne URL-ove u apsolutne
                    if href.startswith('/'):
                        from urllib.parse import urljoin
                        href = urljoin(url, href)
                    if text or href:
                        link_results.append(f"{text}: {href}")
                if link_results:
                    result += f"Links ({len(link_results)}):\n"
                    result += "\n".join(link_results[:limit]) + "\n\n"
        
        if extract == "headings" or extract == "all":
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if headings:
                heading_results = []
                for h in headings[:limit]:
                    text = h.get_text(strip=True)
                    if text:
                        heading_results.append(f"{h.name.upper()}: {text}")
                if heading_results:
                    result += f"Headings ({len(heading_results)}):\n"
                    result += "\n".join(heading_results[:limit]) + "\n\n"
        
        if extract == "text" or extract == "all":
            # Izvuci sav tekst
            text_content = soup.get_text(separator='\n', strip=True)
            # Očisti višestruke prazne linije
            lines = [line for line in text_content.split('\n') if line.strip()]
            text_content = '\n'.join(lines)
            # Limitaj na 3000 karaktera
            if len(text_content) > 3000:
                text_content = text_content[:3000] + "...\n[... rest of text truncated ...]"
            result += f"Text:\n{text_content}\n\n"
        
        if extract == "tables" or extract == "all":
            tables = soup.find_all('table')
            if tables:
                result += f"Tables ({len(tables)}):\n"
                for idx, table in enumerate(tables[:min(3, limit)], 1):
                    result += f"\nTable {idx}:\n"
                    rows = table.find_all('tr')
                    for row in rows[:limit]:
                        cells = row.find_all(['td', 'th'])
                        if cells:
                            cell_texts = [cell.get_text(strip=True) for cell in cells]
                            result += " | ".join(cell_texts[:10]) + "\n"  # Maks 10 kolona
                result += "\n"
        
        if extract == "lists" or extract == "all":
            lists = soup.find_all(['ul', 'ol'])
            if lists:
                list_results = []
                for list_elem in lists[:limit]:
                    items = list_elem.find_all('li')
                    for item in items[:20]:  # Max 20 stavki po listi
                        text = item.get_text(strip=True)
                        if text:
                            list_results.append(f"• {text}")
                if list_results:
                    result += f"Lists ({len(list_results)} items):\n"
                    result += "\n".join(list_results[:limit]) + "\n\n"
        
        if extract == "images" or extract == "all":
            images = soup.find_all('img', src=True)
            if images:
                image_results = []
                for img in images[:limit]:
                    src = img.get('src', '')
                    alt = img.get('alt', 'No description')
                    # Konvertuj relativne URL-ove
                    if src.startswith('/'):
                        from urllib.parse import urljoin
                        src = urljoin(url, src)
                    image_results.append(f"{alt}: {src}")
                if image_results:
                    result += f"Images ({len(image_results)}):\n"
                    result += "\n".join(image_results[:limit]) + "\n\n"
        
        # Ako je extract "all", možda je previše podataka - limitaj
        if extract == "all" and len(result) > 5000:
            result = result[:5000] + "\n[... rest truncated ...]"
        
        return result.strip() if result.strip() else "Could not extract data from page."
        
    except requests.exceptions.Timeout:
        return f"Request timed out for URL {url}."
    except requests.exceptions.ConnectionError:
        return f"No internet connection to access {url}."
    except Exception as e:
        print(f"[GREŠKA] Error u scrape_webpage: {e}")
        return f"Error parsing web page {url}: {str(e)}"
