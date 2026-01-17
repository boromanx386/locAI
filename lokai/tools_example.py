"""
Primer kako da koristiš tools/function calling sa Ollama API-jem.

Ovo pokazuje kako da definišeš tools i kako model može da ih pozove.
"""

import sys
import io
import json

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from lokai.core.ollama_client import OllamaClient

# Primer tool-a za pretragu interneta
def search_web(query: str) -> str:
    """
    Stvarno pretražuje internet koristeći worldtimeapi.org za vreme i DuckDuckGo Instant Answer za ostalo.
    """
    print(f"[TOOL] Pretražujem web za: {query}")
    
    try:
        import requests
        from urllib.parse import quote_plus
        
        # Posebno rukovanje za vreme - koristi worldtimeapi.org (TAČNO VREME!)
        if "vreme" in query.lower() or "time" in query.lower():
            timezone = "Europe/Belgrade"  # Default
            if "beograd" in query.lower() or "belgrade" in query.lower():
                timezone = "Europe/Belgrade"
            elif "london" in query.lower():
                timezone = "Europe/London"
            elif "new york" in query.lower():
                timezone = "America/New_York"
            elif "tokyo" in query.lower():
                timezone = "Asia/Tokyo"
            elif "paris" in query.lower():
                timezone = "Europe/Paris"
            elif "berlin" in query.lower():
                timezone = "Europe/Berlin"
            
            try:
                time_url = f"http://worldtimeapi.org/api/timezone/{timezone}"
                time_response = requests.get(time_url, timeout=5)
                if time_response.status_code == 200:
                    time_data = time_response.json()
                    current_time = time_data.get("datetime", "")
                    timezone_abbr = time_data.get("abbreviation", "")
                    if current_time:
                        # Formatiraj vreme
                        from datetime import datetime
                        dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        city_name = timezone.split('/')[-1].replace('_', ' ')
                        return f"Trenutno vreme u {city_name}: {formatted_time} ({timezone_abbr})"
            except Exception as e:
                print(f"[GREŠKA] Error pri dobijanju vremena: {e}")
                return f"Greška pri dobijanju vremena za {timezone}: {str(e)}"
        
        # Za ostalo - DuckDuckGo Instant Answer API
        ia_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        ia_response = requests.get(ia_url, timeout=5)
        
        if ia_response.status_code == 200:
            ia_data = ia_response.json()
            
            # AbstractText (kratak odgovor)
            if ia_data.get("AbstractText"):
                result = ia_data["AbstractText"]
                if ia_data.get("AbstractURL"):
                    result += f"\nIzvor: {ia_data['AbstractURL']}"
                return result
            
            # Answer (kratak odgovor)
            if ia_data.get("Answer"):
                return ia_data["Answer"]
            
            # RelatedTopics (srodne teme)
            if ia_data.get("RelatedTopics") and len(ia_data["RelatedTopics"]) > 0:
                topics = ia_data["RelatedTopics"][:3]  # Prva 3 rezultata
                results = []
                for topic in topics:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append(topic["Text"][:200])  # Prvih 200 karaktera
                if results:
                    return "\n\n".join(results)
        
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
    Simulira vremensku prognozu. U stvarnosti bi pravio HTTP zahtev ka weather API.
    """
    print(f"[TOOL] Dobijam vremensku prognozu za: {city}")
    if city.lower() in ["beograd", "belgrade"]:
        return "Vremenska prognoza za Beograd:\n- Danas: 15°C, oblačno sa suncem\n- Sutra: 18°C, sunčano\n- Prekosutra: 16°C, kiša"
    return f"Vremenska prognoza za {city}: [nije dostupno]"


# Primer definisanja tools za Ollama
tools_example = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Pretražuje internet za informacije o datoj temi",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - šta treba pretražiti"
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
            "description": "Dobija vremensku prognozu za dati grad",
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


def test_tools():
    """Test primer korišćenja tools sa Ollama."""
    
    client = OllamaClient()
    
    if not client.is_running():
        print("Ollama server nije pokrenut!")
        return
    
    # Proveri da li model podržava tools (npr. qwen3:8b)
    model = "qwen3:8b"  # Ili deepseek-r1:8b ako podržava
    
    print(f"Pozivam model {model} sa tools...")
    print(f"Tools: {len(tools_example)} tool-a definisano")
    print("\n" + "="*60 + "\n")
    
    # TEST 1: Koristi /api/chat endpoint (bolje podržava tools)
    print("TEST 1: Koristim /api/chat endpoint (bolje za tools)")
    
    messages = [
        {
            "role": "user",
            "content": "Pretraži internet za trenutno vreme i vremensku prognozu u Beogradu. KORISTI search_web tool!"
        }
    ]
    
    result = client.chat_with_tools(
        model=model,
        messages=messages,
        tools=tools_example,
        num_ctx=4096,
    )
    
    print("\n=== RAW RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if "error" in result:
        print(f"\n[GREŠKA] {result['error']}")
    else:
        message = result.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])
        
        print("\n=== ODGOVOR ===")
        print(content)
        
        if tool_calls:
            print(f"\n=== TOOL CALLS ({len(tool_calls)}) ===")
            for i, tool_call in enumerate(tool_calls, 1):
                print(f"\nTool Call #{i}:")
                print(json.dumps(tool_call, indent=2, ensure_ascii=False))
        else:
            print("\n[INFO] Nema tool_calls u odgovoru - model možda nije pozvao tool")
    
    print("\n" + "="*60 + "\n")
    
    # TEST 2: Eksplicitniji zahtev
    print("TEST 2: Eksplicitniji zahtev - tražim vreme")
    
    messages2 = [
        {
            "role": "user",
            "content": "Koja je vremenska prognoza za Beograd? MORAŠ da koristiš get_weather tool sa parametrom city='Beograd'."
        }
    ]
    
    result2 = client.chat_with_tools(
        model=model,
        messages=messages2,
        tools=tools_example,
        num_ctx=4096,
    )
    
    if "error" not in result2:
        message2 = result2.get("message", {})
        content2 = message2.get("content", "")
        tool_calls2 = message2.get("tool_calls", [])
        
        print("\n=== ODGOVOR ===")
        print(content2)
        
        if tool_calls2:
            print(f"\n=== TOOL CALLS ({len(tool_calls2)}) ===")
            for i, tool_call in enumerate(tool_calls2, 1):
                print(f"\nTool Call #{i}:")
                print(json.dumps(tool_call, indent=2, ensure_ascii=False))
        else:
            print("\n[INFO] Nema tool_calls - model možda ne podržava tools ili nije pozvao tool")
    
    print("\n" + "="*60 + "\n")
    
    # TEST 3: Kompletan workflow - izvrši tools i pošalji rezultat nazad
    print("TEST 3: Kompletan workflow - izvršavam tools i šaljem rezultat nazad")
    
    messages3 = [
        {
            "role": "user",
            "content": "Koja je vremenska prognoza za Beograd? Koristi get_weather tool."
        }
    ]
    
    # Korak 1: Model poziva tool
    result3 = client.chat_with_tools(
        model=model,
        messages=messages3,
        tools=tools_example,
        num_ctx=4096,
    )
    
    if "error" in result3:
        print(f"[GREŠKA] {result3['error']}")
    else:
        message3 = result3.get("message", {})
        tool_calls3 = message3.get("tool_calls", [])
        
        if tool_calls3:
            print(f"\n[INFO] Model je pozvao {len(tool_calls3)} tool(s)")
            
            # Korak 2: Izvrši tools i prikupi rezultate
            tool_results = []
            for tool_call in tool_calls3:
                func_name = tool_call["function"]["name"]
                func_args = tool_call["function"]["arguments"]
                tool_id = tool_call["id"]
                
                print(f"\n[IZVRŠAVAM] {func_name} sa argumentima: {func_args}")
                
                # Izvrši tool
                if func_name == "search_web":
                    result = search_web(func_args.get("query", ""))
                elif func_name == "get_weather":
                    result = get_weather(func_args.get("city", ""))
                else:
                    result = f"Tool {func_name} nije implementiran"
                
                # Dodaj rezultat u messages za sledeći poziv
                tool_results.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_id,
                    "name": func_name
                })
            
            # Korak 3: Pošalji originalnu poruku + assistant odgovor sa tool calls + tool rezultate
            messages_with_results = messages3.copy()
            messages_with_results.append(message3)  # Dodaj assistant odgovor sa tool calls
            messages_with_results.extend(tool_results)  # Dodaj tool rezultate
            
            # Korak 4: Model generiše finalni odgovor koristeći tool rezultate
            print("\n[INFO] Šaljem tool rezultate nazad modelu...")
            final_result = client.chat_with_tools(
                model=model,
                messages=messages_with_results,
                tools=tools_example,
                num_ctx=4096,
            )
            
            if "error" not in final_result:
                final_message = final_result.get("message", {})
                final_content = final_message.get("content", "")
                
                print("\n=== FINALNI ODGOVOR (sa tool rezultatima) ===")
                print(final_content)
            else:
                print(f"\n[GREŠKA] {final_result['error']}")
        else:
            print("\n[INFO] Model nije pozvao tool - možda ne podržava tools ili odlučio da ne koristi tool")


if __name__ == "__main__":
    test_tools()
