# Korisne Git komande

Kratak pregled komandi za rad u terminalu (bez Sourcetree-a).

---

## Trenutno stanje

| Komanda | Šta radi |
|---------|----------|
| `git status` | Šta je promenjeno, na kojoj si grani |
| `git branch --show-current` | Samo ime trenutne grane |
| `git branch` | Lista lokalnih grana (`*` = trenutna) |
| `git branch -a` | Lokalne + remote grane |
| `git log --oneline -10` | Poslednjih 10 commit-ova |

---

## Grane

| Komanda | Šta radi |
|---------|----------|
| `git checkout main` | Prebaci se na granu `main` |
| `git switch main` | Isto (noviji način) |
| `git checkout -b nova-grana` | Napravi novu granu i prebaci se na nju |
| `git switch -c nova-grana` | Isto (noviji način) |
| `git branch -d ime-grane` | Obriši lokalnu granu (bezbedno) |
| `git branch -D ime-grane` | Forsirano brisanje grane |
| `git merge ime-grane` | Spoji `ime-grane` u trenutnu granu |

---

## Remote (GitHub / GitLab)

| Komanda | Šta radi |
|---------|----------|
| `git remote -v` | Prikaži remote URL-ove |
| `git fetch origin` | Preuzmi promene sa servera (bez merge) |
| `git pull` | Fetch + merge u trenutnu granu |
| `git push` | Pošalji commit-ove na remote |
| `git push -u origin ime-grane` | Prvi push nove grane (postavi tracking) |
| `git push origin --delete ime-grane` | Obriši granu na remote-u |

---

## Commit i fajlovi

| Komanda | Šta radi |
|---------|----------|
| `git add .` | Dodaj sve promene u staging |
| `git add putanja/fajl` | Dodaj samo jedan fajl |
| `git commit -m "Poruka"` | Napravi commit sa porukom |
| `git commit --amend -m "Nova poruka"` | Izmeni poslednji commit (poruku) |
| `git restore fajl` | Odbaci promene u fajlu (nepoželjno) |
| `git restore --staged fajl` | Skini fajl iz staging-a |

---

## Pomoć

| Komanda | Šta radi |
|---------|----------|
| `git help` | Opšta pomoć |
| `git help commit` | Pomoć za npr. `commit` |
| `git komanda --help` | Kratka pomoć za komandu |

---

## Brzi recepti

- **Proveri granu:** `git branch --show-current`
- **Prebaci se na main:** `git checkout main` ili `git switch main`
- **Nova grana i rad na njoj:** `git checkout -b feature-x`
- **Posle izmena – commit i push:**  
  `git add .` → `git commit -m "Opis"` → `git push`
