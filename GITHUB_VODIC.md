# 📚 Detaljan Vodič: Kako da Povežete GitHub i Cursor

Ovaj vodič će vas korak-po-korak provesti kroz proces povezivanja GitHub-a sa Cursor editorom i postavljanja vašeg projekta na GitHub.

---

## 📋 Sadržaj

1. [Prerequisites (Šta vam treba)](#prerequisites)
2. [Instalacija Git-a](#instalacija-git-a)
3. [Kreiranje GitHub naloga](#kreiranje-github-naloga)
4. [Podešavanje Git-a na vašem računaru](#podešavanje-git-a)
5. [Inicijalizacija Git repozitorijuma](#inicijalizacija-git-repozitorijuma)
6. [Kreiranje GitHub repozitorijuma](#kreiranje-github-repozitorijuma)
7. [Povezivanje lokalnog projekta sa GitHub-om](#povezivanje-lokalnog-projekta-sa-github-om)
8. [Upload projekta na GitHub](#upload-projekta-na-github)
9. [Rad sa Cursor-om i Git-om](#rad-sa-cursor-om-i-git-om)
10. [Česti problemi i rešenja](#česti-problemi-i-rešenja)

---

## 🔧 Prerequisites (Šta vam treba)

- Windows računar
- Internet konekcija
- GitHub nalog (ili ćemo ga kreirati)
- Cursor editor (već imate)

---

## 1️⃣ Instalacija Git-a

### Korak 1: Preuzmite Git

1. Idite na: https://git-scm.com/download/win
2. Kliknite na "Download" dugme
3. Preuzmite installer (Git-2.x.x-64-bit.exe)

### Korak 2: Instalirajte Git

1. Pokrenite installer
2. Kliknite "Next" kroz sve korake
3. **Važno**: Ostavite opciju "Git from the command line and also from 3rd-party software" označenu
4. Kliknite "Install"
5. Kada se završi, kliknite "Finish"

### Korak 3: Proverite instalaciju

1. Otvorite **PowerShell** ili **Command Prompt**
2. Ukucajte:
   ```bash
   git --version
   ```
3. Trebalo bi da vidite nešto kao: `git version 2.xx.x`

✅ **Ako vidite verziju, Git je uspešno instaliran!**

---

## 2️⃣ Kreiranje GitHub naloga

### Korak 1: Registracija

1. Idite na: https://github.com
2. Kliknite na "Sign up" (gore desno)
3. Unesite:
   - Email adresu
   - Lozinku (minimalno 8 karaktera, kombinacija slova i brojeva)
   - Korisničko ime (ovo će biti vaš GitHub username)
4. Kliknite "Create account"
5. Potvrdite email adresu (proverite inbox)

### Korak 2: Verifikacija

1. GitHub će vam poslati email sa verifikacionim linkom
2. Kliknite na link u email-u
3. Završite verifikaciju

✅ **Sada imate GitHub nalog!**

---

## 3️⃣ Podešavanje Git-a na vašem računaru

### Korak 1: Konfigurišite vaše ime i email

Otvorite **PowerShell** ili **Command Prompt** i ukucajte:

```bash
git config --global user.name "Vaše Ime"
git config --global user.email "vas@email.com"
```

**Primer:**
```bash
git config --global user.name "Marko Petrovic"
git config --global user.email "marko.petrovic@gmail.com"
```

⚠️ **VAŽNO**: Koristite **ISTI EMAIL** koji ste koristili za GitHub nalog!

### Korak 2: Proverite konfiguraciju

```bash
git config --global --list
```

Trebalo bi da vidite vaše ime i email.

---

## 4️⃣ Inicijalizacija Git repozitorijuma

### Korak 1: Otvorite terminal u Cursor-u

1. U Cursor-u, pritisnite `Ctrl + `` (backtick) ili idite na **Terminal > New Terminal**
2. Terminal će se otvoriti na dnu ekrana

### Korak 2: Navigirajte do vašeg projekta

```bash
cd "q:\coding\ai asist"
```

### Korak 3: Inicijalizujte Git repozitorijum

```bash
git init
```

Ovo kreira `.git` folder u vašem projektu (nećete ga videti, ali je tu).

### Korak 4: Dodajte sve fajlove

```bash
git add .
```

Ovo dodaje sve fajlove u "staging area" (priprema za commit).

### Korak 5: Napravite prvi commit

```bash
git commit -m "Initial commit - prvi upload projekta"
```

✅ **Sada imate lokalni Git repozitorijum!**

---

## 5️⃣ Kreiranje GitHub repozitorijuma

### Korak 1: Idite na GitHub

1. Prijavite se na https://github.com
2. Kliknite na **"+"** ikonu (gore desno)
3. Izaberite **"New repository"**

### Korak 2: Popunite informacije

- **Repository name**: `lokai` ili `ai-assistant` (bez razmaka!)
- **Description**: "Local AI Assistant with LLM, Image Generation, and TTS"
- **Public** ili **Private** (izaberite šta želite)
  - **Public**: Svi mogu da vide
  - **Private**: Samo vi možete da vidite
- **NE** označavajte "Add a README file" (već imate projekat)
- **NE** označavajte "Add .gitignore" (već smo ga kreirali)
- **NE** označavajte "Choose a license" (možete kasnije)

### Korak 3: Kliknite "Create repository"

GitHub će vam pokazati stranicu sa instrukcijama. **NE ZATVARAJTE OVU STRANICU!**

---

## 6️⃣ Povezivanje lokalnog projekta sa GitHub-om

### Korak 1: Kopirajte URL vašeg repozitorijuma

Na GitHub stranici, videćete nešto kao:

```
https://github.com/VAS_USERNAME/lokai.git
```

**Kopirajte ovaj URL!**

### Korak 2: Dodajte remote u terminalu

U Cursor terminalu, ukucajte:

```bash
git remote add origin https://github.com/VAS_USERNAME/lokai.git
```

**Zamenite `VAS_USERNAME` sa vašim GitHub username-om!**

**Primer:**
```bash
git remote add origin https://github.com/markopetrovic/lokai.git
```

### Korak 3: Proverite da li je remote dodat

```bash
git remote -v
```

Trebalo bi da vidite vaš URL.

---

## 7️⃣ Upload projekta na GitHub

### Korak 1: Preimenujte glavnu granu (ako je potrebno)

```bash
git branch -M main
```

### Korak 2: Upload projekta

```bash
git push -u origin main
```

### Korak 3: Autentifikacija

GitHub će tražiti autentifikaciju. Imate **2 opcije**:

#### Opcija A: Personal Access Token (Preporučeno)

1. Idite na: https://github.com/settings/tokens
2. Kliknite **"Generate new token"** > **"Generate new token (classic)"**
3. Unesite "Note" (npr. "Cursor Git Access")
4. Izaberite scope: **"repo"** (sve opcije pod repo)
5. Kliknite **"Generate token"**
6. **KOPIRAJTE TOKEN** (nećete ga moći da vidite ponovo!)
7. Kada Git traži lozinku, **ukucajte token umesto lozinke**

#### Opcija B: GitHub CLI (Naprednije)

```bash
# Instalirajte GitHub CLI
winget install GitHub.cli

# Autentifikujte se
gh auth login
```

### Korak 4: Proverite rezultat

1. Idite na vaš GitHub repozitorijum u browseru
2. Osvežite stranicu (F5)
3. Trebalo bi da vidite sve vaše fajlove! 🎉

---

## 8️⃣ Rad sa Cursor-om i Git-om

### Osnovne Git komande u Cursor terminalu

#### Dodavanje promena
```bash
git add .                    # Dodaje sve promene
git add ime_fajla.py         # Dodaje specifičan fajl
```

#### Commit (snimanje promena)
```bash
git commit -m "Opis promena"
```

**Primeri:**
```bash
git commit -m "Dodata nova funkcionalnost za generisanje slika"
git commit -m "Ispravljena greška u chat widget-u"
git commit -m "Ažuriran README fajl"
```

#### Push (slanje na GitHub)
```bash
git push
```

#### Pull (preuzimanje sa GitHub-a)
```bash
git pull
```

#### Provera statusa
```bash
git status
```

#### Pregled promena
```bash
git log
```

### Git integracija u Cursor-u

Cursor ima ugrađenu Git podršku:

1. **Source Control panel** (levo, ikona grana):
   - Vidite sve promene
   - Možete da commit-ujete direktno iz Cursor-a
   - Možete da push-ujete sa jednim klikom

2. **Git indikatori**:
   - **M** = Modified (izmenjeno)
   - **A** = Added (dodato)
   - **D** = Deleted (obrisano)
   - **U** = Untracked (nepraćeno)

3. **Commit iz Cursor-a**:
   - Otvorite Source Control panel (Ctrl+Shift+G)
   - Unesite commit poruku
   - Kliknite na ✓ (checkmark)
   - Kliknite na "..." > "Push"

---

## 9️⃣ Česti problemi i rešenja

### Problem 1: "fatal: not a git repository"

**Rešenje:**
```bash
git init
```

### Problem 2: "remote origin already exists"

**Rešenje:**
```bash
git remote remove origin
git remote add origin https://github.com/VAS_USERNAME/lokai.git
```

### Problem 3: "Authentication failed"

**Rešenje:**
- Proverite da li koristite Personal Access Token umesto lozinke
- Kreirajte novi token na: https://github.com/settings/tokens

### Problem 4: "Permission denied"

**Rešenje:**
- Proverite da li je token ispravan
- Proverite da li imate prava na repozitorijum

### Problem 5: "Large files" greška

**Rešenje:**
- Veliki fajlovi (preko 100MB) ne mogu na GitHub
- Dodajte ih u `.gitignore`
- Ili koristite Git LFS (Large File Storage)

### Problem 6: "Merge conflict"

**Rešenje:**
```bash
git pull origin main
# Rešite konflikte u fajlovima
git add .
git commit -m "Resolved merge conflicts"
git push
```

---

## 🔄 Tipičan radni tok (Workflow)

### Svakodnevni rad:

1. **Napravite promene** u Cursor-u
2. **Proverite status:**
   ```bash
   git status
   ```
3. **Dodajte promene:**
   ```bash
   git add .
   ```
4. **Commit-ujte:**
   ```bash
   git commit -m "Opis šta ste uradili"
   ```
5. **Push-ujte na GitHub:**
   ```bash
   git push
   ```

### Ako radite sa drugog računara:

1. **Clone repozitorijum:**
   ```bash
   git clone https://github.com/VAS_USERNAME/lokai.git
   ```
2. **Preuzmite najnovije promene:**
   ```bash
   git pull
   ```

---

## 📝 Checklist - Proverite da li ste sve uradili

- [ ] Git je instaliran (`git --version` radi)
- [ ] GitHub nalog je kreiran i verifikovan
- [ ] Git je konfigurisan (ime i email)
- [ ] Git repozitorijum je inicijalizovan (`git init`)
- [ ] `.gitignore` fajl je kreiran
- [ ] Prvi commit je napravljen
- [ ] GitHub repozitorijum je kreiran
- [ ] Remote je dodat (`git remote add origin`)
- [ ] Projekat je upload-ovan (`git push`)
- [ ] Fajlovi su vidljivi na GitHub-u

---

## 🎓 Dodatni resursi

- **Git dokumentacija**: https://git-scm.com/doc
- **GitHub vodiči**: https://docs.github.com
- **GitHub Desktop** (GUI alternativa): https://desktop.github.com

---

## 💡 Saveti

1. **Često commit-ujte**: Bolje je više malih commit-a nego jedan veliki
2. **Dobri commit poruke**: Budite jasni šta ste promenili
3. **Pull pre push**: Uvek `git pull` pre `git push` ako radite sa drugima
4. **Backup**: GitHub je odličan backup vašeg koda
5. **Branches**: Za veće promene, koristite grane (`git branch`)

---

## ❓ Pitanja?

Ako imate problema, proverite:
1. Da li je Git instaliran?
2. Da li je GitHub nalog verifikovan?
3. Da li je token ispravan?
4. Da li je remote URL tačan?

---

**Srećno sa kodiranjem! 🚀**


