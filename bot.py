import os
import discord
from discord.ext import commands
import random
import re

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# HIER DEINE RICHTIGE ROLLEN-ID FEST EINGETRAGEN
ROLLEN_ID = 1487152872331153448 

POSITIONS = [
    discord.SelectOption(label="Torwart (TW)", value="TW", emoji="🧤"),
    discord.SelectOption(label="Innenverteidiger (IV)", value="IV", emoji="🛡️"),
    discord.SelectOption(label="Außenverteidiger (LV/RV)", value="AV", emoji="🏃"),
    discord.SelectOption(label="Defensives Mittelfeld (ZDM)", value="ZDM", emoji="🧠"),
    discord.SelectOption(label="Zentrales Mittelfeld (ZM)", value="ZM", emoji="🔄"),
    discord.SelectOption(label="Zentrales Offensives Mittelfeld (ZOM)", value="ZOM", emoji="🪄"), # ZOM HIER HINZUGEFÜGT
    discord.SelectOption(label="Flügelspieler (LF/RF)", value="Flügel", emoji="⚡"),
    discord.SelectOption(label="Stürmer (ST)", value="ST", emoji="⚽")
]

# ==========================================
#  GEMEINSAME ELEMENTE (DROPDOWNS)
# ==========================================

class PositionSelect(discord.ui.Select):
    def __init__(self, view_instance):
        super().__init__(placeholder="Wähle deine Position...", min_values=1, max_values=1, options=POSITIONS)
        self.view_instance = view_instance

    async def callback(self, interaction: discord.Interaction):
        spieler_name = interaction.user.display_name
        gewaehlte_pos = self.values[0]
        self.view_instance.teilnehmer[interaction.user.id] = (spieler_name, gewaehlte_pos)
        await self.view_instance.main_message.edit(embed=self.view_instance.erstelle_embed())
        await interaction.response.edit_message(content=f"✅ Du hast dich als **{gewaehlte_pos}** eingetragen!", view=None)

# ==========================================
#  SYSTEM 1: DEIN NORMALER MATCHDAY (!termin)
# ==========================================

class TurnierAnmeldungView(discord.ui.View):
    def __init__(self, info_text):
        super().__init__(timeout=None)
        self.teilnehmer = {}
        self.info_text = info_text
        self.main_message = None

    def erstelle_embed(self):
        embed = discord.Embed(
            title="📅 Fc Katalonia Matchday", 
            description=f"ℹ️ **Termin:** {self.info_text}\n\nKlicke unten auf **Teilnehmen**, um dich einzutragen!", 
            color=discord.Color.blue()
        )
        
        if not self.teilnehmer:
            embed.add_field(name="Aufstellung:", value="*Noch keine Anmeldungen*", inline=False)
        else:
            liste_text = ""
            for i, (name, pos) in enumerate(self.teilnehmer.values(), start=1):
                liste_text += f"{i}. **{name}** ({pos})\n"
            embed.add_field(name="Aufstellung:", value=liste_text, inline=False)
            
        return embed

    @discord.ui.button(label="Teilnehmen", style=discord.ButtonStyle.green, custom_id="join_btn")
    async def teilnehmen(self, interaction: discord.Interaction, button: discord.ui.Button):
        dropdown_view = discord.ui.View()
        dropdown_view.add_item(PositionSelect(self))
        await interaction.response.send_message("Auf welcher Position spielst du?", view=dropdown_view, ephemeral=True)

    @discord.ui.button(label="Abmelden", style=discord.ButtonStyle.danger, custom_id="leave_btn")
    async def abmelden(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.teilnehmer:
            del self.teilnehmer[interaction.user.id]
            await self.main_message.edit(embed=self.erstelle_embed())
            await interaction.response.send_message("Du hast dich abgemeldet.", ephemeral=True)
        else:
            await interaction.response.send_message("Du warst gar nicht angemeldet!", ephemeral=True)

# ==========================================
#  SYSTEM 2: DAS NEUE INTERNE MATCH (!internmatch)
# ==========================================
class InternmatchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.teilnehmer = {}  # Speichert das interne Match getrennt ab
        self.main_message = None

    def erstelle_embed(self):
        embed = discord.Embed(
            title="⚔️ FC Katalonia Internmatch", 
            description="Männer, wir splitten heute! Tragt euch ein und gebt eure Position an.\nDer Bot teilt danach automatisch fair auf.", 
            color=discord.Color.orange()
        )
        
        if not self.teilnehmer:
            embed.add_field(name="Aktuelle Anmeldungen:", value="*Noch keine Spieler eingetragen*", inline=False)
        else:
            liste_text = ""
            for i, (name, pos) in enumerate(self.teilnehmer.values(), start=1):
                liste_text += f"{i}. **{name}** ({pos})\n"
            embed.add_field(name="Aktuelle Anmeldungen:", value=liste_text, inline=False)
            
        return embed

    @discord.ui.button(label="Teilnehmen", style=discord.ButtonStyle.green, custom_id="intern_join_btn")
    async def teilnehmen(self, interaction: discord.Interaction, button: discord.ui.Button):
        dropdown_view = discord.ui.View()
        dropdown_view.add_item(PositionSelect(self))
        await interaction.response.send_message("Auf welcher Position spielst du?", view=dropdown_view, ephemeral=True)

    @discord.ui.button(label="Abmelden", style=discord.ButtonStyle.danger, custom_id="intern_leave_btn")
    async def abmelden(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.teilnehmer:
            del self.teilnehmer[interaction.user.id]
            await self.main_message.edit(embed=self.erstelle_embed())
            await interaction.response.send_message("Du hast dich abgemeldet.", ephemeral=True)
        else:
            await interaction.response.send_message("Du warst gar nicht angemeldet!", ephemeral=True)

    @discord.ui.button(label="💥 Teams splitten", style=discord.ButtonStyle.blurple, custom_id="intern_split_btn")
    async def split_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.teilnehmer) < 2:
            await interaction.response.send_message("❌ Es müssen mindestens 2 Spieler angemeldet sein, um zu splitten!", ephemeral=True)
            return

        # --- FAIR SPLIT LOGIK ---
        toepfe = {"TW": [], "Verteidigung": [], "Mittelfeld": [], "Sturm": []}
        
        # Sortierung in die strategischen Töpfe
        for name, pos in self.teilnehmer.values():
            spieler = {"name": name, "pos": pos}
            if pos == "TW":
                toepfe["TW"].append(spieler)
            elif pos in ["IV", "AV"]:
                toepfe["Verteidigung"].append(spieler)
            elif pos in ["ZDM", "ZM", "ZOM"]:
                toepfe["Mittelfeld"].append(spieler)
            elif pos in ["ST", "Flügel"]:
                toepfe["Sturm"].append(spieler)

        team_a = []
        team_b = []
        wexel = True

        # Ausbalancierte, zufällige Zuweisung pro Positionstopf
        for kategorie, spieler_in_kategorie in toepfe.items():
            random.shuffle(spieler_in_kategorie)
            for spieler in spieler_in_kategorie:
                if wexel:
                    team_a.append(spieler)
                else:
                    team_b.append(spieler)
                wexel = not wexel

        # Ergebnisfenster (Embed) bauen
        ergebnis_embed = discord.Embed(title="⚽ Die Teams wurden fair getrennt!", color=discord.Color.gold())
        
        text_a = "\n".join([f"- **{s['name']}** ({s['pos']})" for s in team_a]) if team_a else "_Keine Spieler_"
        text_b = "\n".join([f"- **{s['name']}** ({s['pos']})" for s in team_b]) if team_b else "_Keine Spieler_"
        
        ergebnis_embed.add_field(name="🟢 TEAM A", value=text_a, inline=False)
        ergebnis_embed.add_field(name="🔴 TEAM B", value=text_b, inline=False)

        # Das Ergebnis wird als normale Nachricht in den Chat gepostet
        await interaction.response.send_message(embed=ergebnis_embed)


# ==========================================
#  SYSTEM 3: AUFSTELLUNG (!aufstellung)
# ==========================================

# Eure Formationen: Name -> Positionen in der Reihenfolge, in der der Bot fragt.
# Hier einfach anpassen, löschen oder neue hinzufügen (max. 25).
# (Der Torwart zählt im Namen nicht mit: 3-5-2 heißt 1 TW + 3-5-2.)
FORMATIONEN = {
    "3-5-2 (defensiv)": ["TW", "IV", "IV", "IV", "LZDM", "RZDM", "ZOM", "LM", "RM", "ST", "ST"],
    "3-5-2 (neutral)": ["TW", "IV", "IV", "IV", "LZM", "RZM", "ZOM", "LM", "RM", "ST", "ST"],
    "4-3-3": ["TW", "LV", "IV", "IV", "RV", "LZM", "RZM", "ZOM", "LF", "RF", "ST"],
}

# Welche Discord-Rollen (Name, Groß/Klein egal) für eine Position angezeigt werden.
# Steht eine Position hier nicht drin, wird die Rolle mit genau diesem Namen gesucht
# (z.B. TW -> Rolle "TW", LF -> Rolle "LF").
ROLLEN_PRO_POSITION = {
    "LZDM": ["ZDM"],
    "RZDM": ["ZDM"],
    "LZM": ["ZM"],
    "RZM": ["ZM"],
    "LM": ["LF"],
    "RM": ["RF"],
}


def rolle_passt(rollen_name: str, kuerzel: str) -> bool:
    """True, wenn das Kürzel als eigenes Wort im Rollennamen steht.
    Passt z.B. bei "TW", "🧤 TW", "TW | Torwart" - aber nicht "ZM" in "ZDM" oder "ST" in "Stürmer"."""
    muster = rf"(?<![A-Za-zÄÖÜäöüß]){re.escape(kuerzel)}(?![A-Za-zÄÖÜäöüß])"
    return re.search(muster, rollen_name, re.IGNORECASE) is not None


def spieler_mit_rolle(guild: discord.Guild, position: str):
    """Alle Mitglieder (ohne Bots), die eine passende Rolle für die Position haben.
    Gibt (Spielerliste, Namen der gefundenen Rollen) zurück."""
    kuerzel = ROLLEN_PRO_POSITION.get(position, [position])
    gefunden = {}
    rollen = []
    for rolle in guild.roles:
        if any(rolle_passt(rolle.name, k) for k in kuerzel):
            rollen.append(rolle.name)
            for member in rolle.members:
                if not member.bot:
                    gefunden[member.id] = member
    spieler = sorted(gefunden.values(), key=lambda m: m.display_name.lower())
    return spieler, rollen


class FormationSelect(discord.ui.Select):
    def __init__(self, autor_id):
        options = [discord.SelectOption(label=name, value=name, emoji="📋") for name in FORMATIONEN]
        super().__init__(placeholder="Welche Aufstellung?", min_values=1, max_values=1, options=options)
        self.autor_id = autor_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message("❌ Nur wer den Befehl gestartet hat, darf das.", ephemeral=True)
            return
        builder = AufstellungBuilder(self.autor_id, self.values[0], interaction.guild)
        # Weiter geht's in einer Nachricht, die nur der Ersteller sieht
        await interaction.response.send_message(content=builder.text(), view=builder, ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass


class SpielerSelect(discord.ui.Select):
    def __init__(self, builder, kandidaten):
        options = [
            discord.SelectOption(label=m.display_name[:100], value=str(m.id))
            for m in kandidaten[:24]
        ]
        options.append(discord.SelectOption(label="Position frei lassen", value="0", emoji="➖"))
        super().__init__(
            placeholder=f"Spieler für {builder.aktuelle_position()} wählen...",
            min_values=1, max_values=1, options=options,
        )
        self.builder = builder

    async def callback(self, interaction: discord.Interaction):
        wert = int(self.values[0])
        member = interaction.guild.get_member(wert) if wert else None
        await self.builder.eintragen(interaction, member)


class AndererSpielerSelect(discord.ui.UserSelect):
    """Fallback: beliebiges Mitglied wählen (z.B. wenn keiner die Rolle hat)."""
    def __init__(self, builder):
        super().__init__(placeholder="...oder anderes Mitglied suchen", min_values=1, max_values=1)
        self.builder = builder

    async def callback(self, interaction: discord.Interaction):
        member = self.values[0]
        if member.id in self.builder.vergebene_ids():
            await interaction.response.send_message("❌ Der Spieler ist schon aufgestellt.", ephemeral=True)
            return
        await self.builder.eintragen(interaction, member)


class AufstellungBuilder(discord.ui.View):
    def __init__(self, autor_id, formation, guild):
        super().__init__(timeout=900)
        self.autor_id = autor_id
        self.formation = formation
        self.positionen = FORMATIONEN[formation]
        self.guild = guild
        self.auswahl = []  # Liste von Member oder None, parallel zu self.positionen
        self.baue_komponenten()

    def aktuelle_position(self):
        return self.positionen[len(self.auswahl)]

    def vergebene_ids(self):
        return {m.id for m in self.auswahl if m}

    def text(self):
        zeilen = [f"📋 **Aufstellung {self.formation}** — Position {len(self.auswahl) + 1}/{len(self.positionen)}"]
        for pos, m in zip(self.positionen, self.auswahl):
            zeilen.append(f"✅ {pos}: {m.display_name if m else '*frei*'}")
        zeilen.append(f"\n👉 Wer spielt **{self.aktuelle_position()}**?")
        if self.hinweis:
            zeilen.append(self.hinweis)
        return "\n".join(zeilen)

    def baue_komponenten(self):
        self.clear_items()
        vergeben = self.vergebene_ids()
        position = self.aktuelle_position()
        spieler, rollen = spieler_mit_rolle(self.guild, position)
        kandidaten = [m for m in spieler if m.id not in vergeben]

        # Hinweis, falls die Liste leer ist - damit man sieht, woran es liegt
        if not rollen:
            gesucht = ", ".join(ROLLEN_PRO_POSITION.get(position, [position]))
            self.hinweis = f"⚠️ Keine Discord-Rolle gefunden, die **{gesucht}** heißt."
        elif not spieler:
            self.hinweis = f"⚠️ Rolle gefunden ({', '.join(rollen)}), aber der Bot sieht keine Mitglieder damit."
        else:
            self.hinweis = ""
        self.add_item(SpielerSelect(self, kandidaten))
        self.add_item(AndererSpielerSelect(self))

        zurueck = discord.ui.Button(label="Zurück", style=discord.ButtonStyle.secondary, emoji="↩️",
                                    disabled=not self.auswahl, row=2)
        zurueck.callback = self.zurueck
        self.add_item(zurueck)

        abbrechen = discord.ui.Button(label="Abbrechen", style=discord.ButtonStyle.danger, row=2)
        abbrechen.callback = self.abbrechen
        self.add_item(abbrechen)

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.autor_id

    async def eintragen(self, interaction: discord.Interaction, member):
        self.auswahl.append(member)
        if len(self.auswahl) < len(self.positionen):
            self.baue_komponenten()
            await interaction.response.edit_message(content=self.text(), view=self)
            return

        # Aufstellung voll -> posten
        self.stop()
        await interaction.response.edit_message(content="✅ Aufstellung wurde gepostet!", view=None)
        embed = discord.Embed(title=f"📋 FC Katalonia Aufstellung ({self.formation})", color=discord.Color.green())
        zeilen = [f"**{pos}** — {m.mention if m else '*frei*'}" for pos, m in zip(self.positionen, self.auswahl)]
        embed.description = "\n".join(zeilen)
        embed.set_footer(text=f"Aufgestellt von {interaction.user.display_name}")
        pings = " ".join(m.mention for m in self.auswahl if m)
        await interaction.channel.send(
            content=pings or None, embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )

    async def zurueck(self, interaction: discord.Interaction):
        if self.auswahl:
            self.auswahl.pop()
        self.baue_komponenten()
        await interaction.response.edit_message(content=self.text(), view=self)

    async def abbrechen(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.edit_message(content="❌ Aufstellung abgebrochen.", view=None)


# ==========================================
#  COMMANDS
# ==========================================


@bot.event
async def on_ready():
    print(f"Bot ist online als {bot.user}")

@bot.command()
async def termin(ctx, *, info: str = "Keine Details angegeben"):
    view = TurnierAnmeldungView(info_text=info)
    await ctx.message.delete()
    
    rollen_ping = f"<@&{ROLLEN_ID}>"
    
    msg = await ctx.send(content=rollen_ping, embed=view.erstelle_embed(), view=view)
    view.main_message = msg
    
@bot.command()
async def internmatch(ctx):
    view = InternmatchView()
    await ctx.message.delete() # Löscht die eingegebene Nachricht

    rollen_ping = f"<@&{ROLLEN_ID}>"
    msg = await ctx.send(content=rollen_ping, embed=view.erstelle_embed(), view=view)
    view.main_message = msg

@bot.command()
async def aufstellung(ctx):
    view = discord.ui.View(timeout=300)
    view.add_item(FormationSelect(ctx.author.id))
    try:
        await ctx.message.delete()
    except discord.NotFound:
        # Nachricht schon weg -> ein zweiter Bot-Prozess hat den Befehl schon bearbeitet
        return
    # Sicherstellen, dass der Bot alle Mitglieder samt Rollen kennt
    if not ctx.guild.chunked:
        await ctx.guild.chunk()
    await ctx.send(f"{ctx.author.mention} Welche Aufstellung spielen wir?", view=view, delete_after=300)

# ZIEHT DAS TOKEN SICHER AUS DEN RENDER-ENVIRONMENT-EINSTELLUNGEN
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)