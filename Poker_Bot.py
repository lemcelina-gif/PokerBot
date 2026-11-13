"""
╔══════════════════════════════════════════════════════════════╗
║         FULLHOUSE HACKATHON — BOT TEMPLATE v1.0              ║
║         No-Limit Texas Hold'em, 6-max                        ║
╚══════════════════════════════════════════════════════════════╝

RULES:
  - Implement the decide() function below. That's it.
  - You may import any stdlib module and any library in requirements.txt
  - You may NOT make network calls or read/write files
  - You have 2 seconds to return an action or you auto-fold
  - If your function crashes, it auto-folds for that hand

CARD FORMAT:
  Cards are strings like "As" (Ace of spades), "Td" (Ten of diamonds)
  Ranks: 2 3 4 5 6 7 8 9 T J Q K A
  Suits: s (spades) h (hearts) d (diamonds) c (clubs)

RETURN FORMAT:
  {"action": "fold"}
  {"action": "check"}          # only valid when amount_owed == 0
  {"action": "call"}
  {"action": "raise", "amount": 1200}   # amount = TOTAL bet, not raise-by
  {"action": "all_in"}

  Invalid actions default to fold. Raises below min_raise_to are snapped up.
"""

# ── You may add imports here ──────────────────────────────────────────────────
import random
# ─────────────────────────────────────────────────────────────────────────────

# ----------------------------------------------------------------------------
# SETUP
# constants, parameters etc.
# ----------------------------------------------------------------------------

BOT_NAME = "SigmaRunner"
BOT_AVATAR = "robot_1"

BIG_BLIND = 100
SMALL_BLIND = 50

OPEN_RAISE_SIZE = 5.0
THREE_BET_MULTIPLIER = 3.5
PREMIUM_RERAISE_MULTIPLIER = 2.3

NUT_BET_SIZE_FLOP = 0.75
STRONG_BET_SIZE_FLOP = 0.65
MEDIUM_BET_SIZE_FLOP = 0.55
TOP_PAIR_BET_SIZE_FLOP = 0.45

NUT_BET_SIZE_TURN = 0.85
STRONG_BET_SIZE_TURN = 0.75
MEDIUM_BET_SIZE_TURN = 0.65
TOP_PAIR_BET_SIZE_TURN = 0.55

RIVER_VALUE_BET_SIZE = 0.9
RIVER_BLUFF_BET_SIZE = 0.5
RIVER_BLUFF_FREQ = 0.10

MIN_KICKER = 11

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SEATS = ["BTN", "SB", "BB", "Utgp1", "UTG", "MP"]


# ----------------------------------------------------------------------------
# HELPERS
# hands Classification
# ----------------------------------------------------------------------------

def isGreater(card0, card1):
  return RANKS.index(card0[0]) > RANKS.index(card1[0])

def numRank(card):
  return RANKS.index(card[0]) + 2

def haveRank(hand, rank):
  return hand[0][0] == rank or hand[1][0] == rank

def isSuited(hand):
  return hand[0][1] == hand[1][1]

def haveRankSuited(hand, rank):
  return isSuited(hand) and haveRank(hand, rank)

def isPair(hand):
  return hand[0][0] == hand[1][0]

def otherCard(hand, rank):
  if hand[0][0] == rank:
    return hand[1]
  return hand[0]

def lowRank(hand):
  return min(numRank(hand[0]), numRank(hand[1]))

def isConnector(hand):
  return abs(numRank(hand[0]) - numRank(hand[1])) == 1

def isOneGapper(hand):
  return abs(numRank(hand[0]) - numRank(hand[1])) == 2


# ----------------------------------------------------------------------------
# HELPERS
# Bet Ranks
# ----------------------------------------------------------------------------

def isPremium(hand):
  # AA or KK -> always all-in / 4-bet
  return isPair(hand) and numRank(hand[0]) >= 13

def should3Bet(hand):
  if isPair(hand):
    return numRank(hand[0]) >= 10  # TT+
  
  if haveRank(hand, "A"):
    other = otherCard(hand, "A")
    if isSuited(hand):
      return numRank(other) >= 12  # AQs+
    return numRank(other) >= 12    # AQo+

  return False

def should3BetIP(hand):
  if haveRankSuited(hand, "A"):
      other = otherCard(hand, "A")
      if numRank(other) >= 10:  
          return True
      if numRank(other) in [4, 5]:  # A4s, A5s
          return True
  if haveRankSuited(hand, "K"):
      other = otherCard(hand, "K")
      if numRank(other) >= 11:
          return True
  if haveRankSuited(hand, "Q"):
      other = otherCard(hand, "Q")
      if numRank(other) == 11:
          return True
  return False

def shouldCall3Bet(hand):
  if isPair(hand):
    r = numRank(hand[0])
    return 9 <= r <= 12

  if haveRank(hand, "A") and isSuited(hand):
    other = otherCard(hand, "A")
    return numRank(other) >= 12

  if haveRank(hand, "A") and haveRank(hand, "K"):
    return True

  if haveRank(hand, "K") and haveRank(hand, "Q") and isSuited(hand):
    return True

  return False

def getOpenRaiserCount(game_state):
  raises = 0
  for a in game_state["action_log"]:
    if a["action"] in ("raise", "bet"):
      raises += 1
  return raises

# ----------------------------------------------------------------------------
# Preflop
# ----------------------------------------------------------------------------

def preflopAction(game_state, hand, ip_call=False):
  cb = game_state["amount_owed"]
  current_bet = game_state["current_bet"]
  min_raise_to = game_state["min_raise_to"]
  my_bet = game_state["your_bet_this_street"]
  stack = game_state["your_stack"]
  max_total = stack + my_bet

  if current_bet >= int(0.4 * stack):
    if isPremium(hand):
      return {"action": "all_in"}
    if should3Bet(hand):
      return {"action": "call"}
    return {"action": "fold"}

  if my_bet > BIG_BLIND and current_bet <= 400:
    return {"action": "call"}

  if cb == 0 or current_bet == BIG_BLIND:
    if int(OPEN_RAISE_SIZE * BIG_BLIND) >= int(0.45 * stack):
      if isPremium(hand):
        return {"action": "all_in"}
      return {"action": "fold"}
    return {"action": "raise", "amount": min(int(OPEN_RAISE_SIZE * BIG_BLIND), max_total)}

  if my_bet == 0 and current_bet <= 3 * BIG_BLIND:
    if should3Bet(hand):
      amount = max(min_raise_to, int(current_bet * THREE_BET_MULTIPLIER))
      if amount >= int(0.15 * stack):
        return {"action": "call"}
      return {"action": "raise", "amount": min(amount, max_total)}
    if ip_call and should3BetIP(hand):
      return {"action": "call"}
    return {"action": "fold"}

  if current_bet <= 6 * BIG_BLIND:
    if isPremium(hand):
      amount = max(min_raise_to, int(current_bet * PREMIUM_RERAISE_MULTIPLIER))
      return {"action": "raise", "amount": min(amount, max_total)}
    if shouldCall3Bet(hand):
      if current_bet >= int(0.15 * stack):
        return {"action": "fold"}
      return {"action": "call"}
    return {"action": "fold"}

  if isPremium(hand):
    return {"action": "call"}
  return {"action": "fold"}

# ----------------------------------------------------------------------------
# Position
# ----------------------------------------------------------------------------

def getPosition(game_state):
  seat = game_state["seat_to_act"]
  players = game_state["players"]
  alog = game_state["action_log"]

  # Aktive Seats
  active_seats = set(
    p["seat"] for p in players
    if p["state"] != "busted"
  )

  n = len(active_seats)

  sb_seat = None
  for a in alog:
    if a["action"] == "small_blind":
      sb_seat = a["seat"]

  if sb_seat is None:
    return "MP"

  return SEATS[-(1 + seat - sb_seat) % n]


def isInPosition(game_state):
  return getPosition(game_state) == "BTN"

# ----------------------------------------------------------------------------
# PREFLOP TACTIC
# ----------------------------------------------------------------------------

def Utgp1(hand, game_state):
  if (
    (isPair(hand) and numRank(hand[1]) >= 4) or
    (haveRankSuited(hand, "A") and numRank(hand[1]) > 8) or
    (haveRank(hand, "A") and numRank(hand[1]) > 10) or
    (haveRankSuited(hand, "K") and numRank(hand[1]) > 9) or
    (haveRank(hand, "K") and numRank(hand[1]) > 11) or
    (haveRankSuited(hand, "Q") and numRank(hand[1]) > 10) or
    (isSuited(hand) and isConnector(hand) and lowRank(hand) >= 7)
  ):
    return preflopAction(game_state, hand, ip_call=True)
  return {"action": "fold"}

def Utg(hand, game_state):
  if (
    (isPair(hand) and numRank(hand[1]) >= 4) or                
    (haveRankSuited(hand, "A") and numRank(hand[1]) > 9) or    
    (haveRank(hand, "A") and numRank(hand[1]) > 10) or         
    (haveRankSuited(hand, "K") and numRank(hand[1]) > 9) or    
    (haveRank(hand, "K") and numRank(hand[1]) > 10) or         
    (haveRankSuited(hand, "Q") and numRank(hand[1]) > 10) or  
    (haveRank(hand, "Q") and numRank(hand[1]) > 10)  
  ):
    return preflopAction(game_state, hand, ip_call=True)
  return {"action": "fold"}

def MP(hand, game_state):
  if (
    (isPair(hand) and numRank(hand[1]) >= 2) or
    (haveRankSuited(hand, "A") and numRank(hand[1]) > 0) or
    (haveRank(hand, "A") and numRank(hand[1]) > 5) or
    (haveRankSuited(hand, "K") and numRank(hand[1]) > 5) or
    (haveRank(hand, "K") and numRank(hand[1]) > 8) or
    (haveRankSuited(hand, "Q") and numRank(hand[1]) > 6) or
    (haveRank(hand, "Q") and numRank(hand[1]) > 8) or
    (haveRankSuited(hand, "J") and numRank(hand[1]) > 6) or
    (haveRank(hand, "J") and numRank(hand[1]) > 8) or
    (isSuited(hand) and isConnector(hand) and lowRank(hand) >= 3) or
    (isSuited(hand) and isOneGapper(hand) and lowRank(hand) >= 2)
  ):
    return preflopAction(game_state, hand, ip_call=True)
  return {"action": "fold"}

def BTN(hand, game_state):
  if (
    (isPair(hand) and numRank(hand[1]) >= 2) or
    (haveRankSuited(hand, "A")) or
    (haveRank(hand, "A") and numRank(hand[1]) > 4) or
    (haveRankSuited(hand, "K")) or
    (haveRank(hand, "K") and numRank(hand[1]) > 5) or
    (haveRankSuited(hand, "Q") and numRank(hand[1]) > 6) or
    (haveRank(hand, "Q") and numRank(hand[1]) > 5) or
    (haveRankSuited(hand, "J") and numRank(hand[1]) > 6) or
    (haveRank(hand, "J") and numRank(hand[1]) > 7) or
    (isSuited(hand) and isConnector(hand) and lowRank(hand) >= 2) or
    (isSuited(hand) and isOneGapper(hand) and lowRank(hand) >= 4)
  ):
    return preflopAction(game_state, hand, ip_call=True)
  return {"action": "fold"}


# ----------------------------------------------------------------------------
# PREFLOP TACTIC SB
# ----------------------------------------------------------------------------

def SB(hand, game_state):
  current_bet = game_state["current_bet"]
  min_raise_to = game_state["min_raise_to"]
  my_bet = game_state["your_bet_this_street"]
  stack = game_state["your_stack"]
  max_total = stack + my_bet

  if isPremium(hand):
    return {"action": "all_in"}

  sb_3bet_range = (
    (isPair(hand) and numRank(hand[1]) >= 9) or
    (haveRankSuited(hand, "A") and numRank(hand[1]) > 10) or
    (haveRank(hand, "A") and numRank(hand[1]) > 12) or
    (haveRankSuited(hand, "K") and numRank(hand[1]) > 11)
  )

  sb_open_range = (
    (isPair(hand) and numRank(hand[1]) >= 2) or
    (haveRankSuited(hand, "A")) or
    (haveRank(hand, "A") and numRank(hand[1]) > 5) or
    (haveRankSuited(hand, "K") and numRank(hand[1]) > 5) or
    (haveRank(hand, "K") and numRank(hand[1]) > 8) or
    (haveRankSuited(hand, "Q") and numRank(hand[1]) > 6) or
    (haveRankSuited(hand, "J") and numRank(hand[1]) > 8) or
    (isSuited(hand) and isConnector(hand) and lowRank(hand) >= 3)
  )

  raiser_count = getOpenRaiserCount(game_state)

  if raiser_count == 0:
    if sb_open_range:
      return {"action": "raise", "amount": min(int(OPEN_RAISE_SIZE * BIG_BLIND), max_total)}
    return {"action": "fold"}

  if raiser_count == 1:
    if my_bet > BIG_BLIND // 2:
      if isPremium(hand):
        return {"action": "all_in"}
      if shouldCall3Bet(hand) and current_bet <= int(0.15 * stack):
        return {"action": "call"}
      return {"action": "fold"}
    if sb_3bet_range:
      amount = max(min_raise_to, int(current_bet * THREE_BET_MULTIPLIER))
      amount = min(amount, int(0.15 * stack))
      return {"action": "raise", "amount": min(amount, max_total)}
    return {"action": "fold"}

  if raiser_count >= 2:
    if isPremium(hand):
      return {"action": "all_in"}
    if sb_3bet_range and current_bet <= int(0.15 * stack):
      return {"action": "call"}
    return {"action": "fold"}

# ----------------------------------------------------------------------------
# PREFLOP TACTIC BB
# ----------------------------------------------------------------------------

def BB(hand, game_state):
  current_bet = game_state["current_bet"]
  min_raise_to = game_state["min_raise_to"]
  my_bet = game_state["your_bet_this_street"]
  stack = game_state["your_stack"]
  max_total = stack + my_bet
  amount_owed = game_state["amount_owed"]

  if isPremium(hand):
    return {"action": "all_in"}

  bb_3bet_one_raiser = (
    (isPair(hand) and numRank(hand[1]) >= 7) or
    (haveRankSuited(hand, "A") and numRank(hand[1]) > 8) or
    (haveRank(hand, "A") and numRank(hand[1]) > 11) or
    (haveRankSuited(hand, "K") and numRank(hand[1]) > 9) or
    (haveRankSuited(hand, "Q") and numRank(hand[1]) > 10)
  )
  bb_3bet_multiway = (
    (isPair(hand) and numRank(hand[1]) >= 10) or
    (haveRankSuited(hand, "A") and numRank(hand[1]) > 12) or
    (haveRank(hand, "A") and numRank(hand[1]) > 12)
  )

  raiser_count = getOpenRaiserCount(game_state)

  if current_bet <= BIG_BLIND or amount_owed == 0:
    if amount_owed == 0:
      return {"action": "check"}
    if bb_3bet_one_raiser:
      return {"action": "raise", "amount": min(int(OPEN_RAISE_SIZE * BIG_BLIND), max_total)}
    return {"action": "call"}

  if raiser_count >= 2:
    if bb_3bet_multiway:
      amount = max(min_raise_to, int(current_bet * THREE_BET_MULTIPLIER))
      amount = min(amount, int(0.15 * stack))
      return {"action": "raise", "amount": min(amount, max_total)}
    if current_bet <= int(0.12 * stack):
      return {"action": "call"}
    return {"action": "fold"}

  if my_bet > BIG_BLIND:
    if isPremium(hand):
      return {"action": "all_in"}
    if bb_3bet_one_raiser and current_bet <= int(0.15 * stack):
      return {"action": "call"}
    return {"action": "fold"}

  if bb_3bet_one_raiser:
    amount = max(min_raise_to, int(current_bet * THREE_BET_MULTIPLIER))
    if amount >= int(0.15 * stack):
      return {"action": "call"}
    return {"action": "raise", "amount": min(amount, max_total)}
  return {"action": "fold"}

PREFLOP_FUNCTIONS_DICT = {"Utgp1": Utgp1, "UTG": Utg, "MP": MP, "BTN": BTN, "SB": SB, "BB": BB}

# ----------------------------------------------------------------------------
# POSTFLOP
# helpers, check board
# ----------------------------------------------------------------------------

def countOvercardOuts(hand, board):
  highest_board = max(numRank(card) for card in board)
  count = 0
  for card in hand:
    if numRank(card) > highest_board:
      count += 1
  return 3 * count

def countRanks(cards):
  ranks = {}
  for card in cards:
    rank = card[0]
    if rank not in ranks:
      ranks[rank] = 0
    ranks[rank] += 1
  return ranks

def countSuits(cards):
  suits = {}
  for card in cards:
    suit = card[1]
    if suit not in suits:
      suits[suit] = 0
    suits[suit] += 1
  return suits

def getRanks(cards):
  ranks = sorted(set(numRank(card) for card in cards))
  if 14 in ranks:
    ranks.append(1)
    ranks = sorted(set(ranks))
  return ranks

def hasPair(cards):
  counts = countRanks(cards).values()
  return any(c >= 2 for c in counts)

def hasTopPair(hand, board):
  highest_board = max(numRank(card) for card in board)
  return any(numRank(card) == highest_board for card in hand)

def hasStrongTopPair(hand, board):
  if not hasTopPair(hand, board):
    return False
  highest_board = max(numRank(card) for card in board)
  for card in hand:
    if numRank(card) != highest_board:
      return numRank(card) >= MIN_KICKER
  return False

def hasTwoPair(cards):
  counts = countRanks(cards).values()
  return sum(c >= 2 for c in counts) >= 2

def hasTwoPairWithHand(hand, board):  # neue Funktion für postflopAction
  rank_counts = countRanks(hand + board)
  pairs = [rank for rank, cnt in rank_counts.items() if cnt >= 2]
  hand_ranks = [c[0] for c in hand]
  pairs_with_hand = [p for p in pairs if p in hand_ranks]
  return len(pairs_with_hand) >= 2

def hasTripsInHand(hand, board):
  rank_counts_all = countRanks(hand + board)
  for rank, count in rank_counts_all.items():
    if count >= 3:
      if any(c[0] == rank for c in hand):
        return True
  return False

def hasQuads(cards):
  counts = countRanks(cards).values()
  return any(c >= 4 for c in counts)

def hasFullHouse(cards):
  counts = list(countRanks(cards).values())
  triples = sum(c >= 3 for c in counts)
  pairs = sum(c >= 2 for c in counts)
  return triples >= 1 and pairs >= 2

def hasFlushDraw(cards):
  suits = countSuits(cards)
  for suit in suits:
    if suits[suit] == 4:
      return True
  return False

def hasOpenEndedStraightDraw(cards):
  ranks = getRanks(cards)
  for i in range(len(ranks) - 3):
    four = ranks[i:i+4]
    if four[3] - four[0] == 3:
      return True
  return False

def hasGutshotDraw(cards):
  ranks = getRanks(cards)
  for i in range(len(ranks) - 3):
    four = ranks[i:i+4]
    if four[3] - four[0] == 4:
      return True
  return False

def countOuts(hand, board):
  outs = 0
  cards = hand + board
  if hasFlushDraw(cards):
    outs += 9
  if hasOpenEndedStraightDraw(cards):
    outs += 8
  elif hasGutshotDraw(cards):
    outs += 4
  if not hasPair(cards) or hasTopPair(hand, board):
    outs += countOvercardOuts(hand, board)
  return outs

def hasFlush(cards):
  suits = countSuits(cards)
  for suit in suits:
    if suits[suit] >= 5:
      return True
  return False

def hasStraight(cards):
  ranks = getRanks(cards)
  for i in range(len(ranks) - 4):
    five = ranks[i:i+5]
    if five[4] - five[0] == 4:
      return True
  return False

def hasStraightFlush(cards):
  for suit in ["h", "d", "c", "s"]:
    suited_cards = [card for card in cards if card[1] == suit]
    if len(suited_cards) >= 5:
      if hasStraight(suited_cards):
        return True
  return False

def betPotPercent(game_state, percent):
  pot = game_state["pot"]
  stack = game_state["your_stack"]
  my_bet = game_state["your_bet_this_street"]
  max_total = stack + my_bet
  amount = max(game_state["min_raise_to"], int(pot * percent))
  return {"action": "raise", "amount": min(amount, max_total)}

# ----------------------------------------------------------------------------
# POSTFLOP
# decision making
# ----------------------------------------------------------------------------

def postflopAction(game_state, hand):
  board = game_state["community_cards"]
  call = game_state["amount_owed"]
  pot = game_state["pot"]
  cards = hand + board
  ip = isInPosition(game_state)
  street = game_state["street"]
  nut_size = NUT_BET_SIZE_FLOP if street == "flop" else NUT_BET_SIZE_TURN
  strong_size = STRONG_BET_SIZE_FLOP if street == "flop" else STRONG_BET_SIZE_TURN
  medium_size = MEDIUM_BET_SIZE_FLOP if street == "flop" else MEDIUM_BET_SIZE_TURN
  top_pair_size = TOP_PAIR_BET_SIZE_FLOP if street == "flop" else TOP_PAIR_BET_SIZE_TURN

  outs = countOuts(hand, board)
  equity = 0
  if street == "flop":
    equity = outs * 4 / 100
  elif street == "turn":
    equity = outs * 2 / 100

  if hasStraightFlush(cards) or hasQuads(cards) or hasFullHouse(cards):
    if call == 0:
      return betPotPercent(game_state, nut_size)
    if call <= int(0.7 * pot):
      return betPotPercent(game_state, nut_size)
    return {"action": "call"}

  if hasFlush(cards) or hasStraight(cards) or hasTripsInHand(hand, board):
    if call == 0:
      return betPotPercent(game_state, strong_size)
    if call <= int(0.5 * pot):
      return betPotPercent(game_state, strong_size)
    if call <= int(0.8 * pot):
      return {"action": "call"}
    return {"action": "fold"}

  if hasTwoPairWithHand(hand, board):
    if call == 0:
      return betPotPercent(game_state, medium_size)
    if call <= int(0.35 * pot):
      return betPotPercent(game_state, medium_size)
    if call <= int(0.6 * pot):
      return {"action": "call"}
    return {"action": "fold"}

  if hasStrongTopPair(hand, board):
    if call == 0:
      return betPotPercent(game_state, top_pair_size)
    if call <= int(0.33 * pot):
      return betPotPercent(game_state, top_pair_size)
    if call <= int(0.5 * pot):
      return {"action": "call"}
    return {"action": "fold"}

  if hasTopPair(hand, board):
    if call == 0:
      if ip:
        return betPotPercent(game_state, top_pair_size)
      return {"action": "check"}
    return {"action": "fold"}
  
  if call == 0 and street in ("flop", "turn"):
    if outs >= 8:
      return betPotPercent(game_state, 0.45)
    if ip and outs >= 4:
      return betPotPercent(game_state, 0.35)

  if street == "river" and call == 0:
    if ip and not hasPair(cards) and random.random() < RIVER_BLUFF_FREQ:
      return betPotPercent(game_state, RIVER_BLUFF_BET_SIZE)

  if call > 0:
    pot_odds = call / (pot + call)
    if equity >= pot_odds and call <= int(0.25 * pot) and street in ("flop", "turn"):
      return betPotPercent(game_state, 0.5)
    if equity >= pot_odds:
      return {"action": "call"}

  if call == 0:
    return {"action": "check"}

  return {"action": "fold"}

# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def decide(state: dict) -> dict:
  game_state = state

  hand = game_state["your_cards"]
  if isGreater(hand[1], hand[0]):
    hand = [hand[1], hand[0]]

  if game_state["street"] != "preflop":
    return postflopAction(game_state, hand)

  pos = getPosition(game_state)

  try:
    return PREFLOP_FUNCTIONS_DICT[pos](hand, game_state)
  except:
    return {"action": "fold"}

 
