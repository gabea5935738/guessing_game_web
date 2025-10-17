from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from random import randint
from time import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = True

@app.before_request
def session_set_cleanup():
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(i) for i in obj]
        else:
            return obj
    for k in list(session.keys()):
        session[k] = convert_sets(session[k])
# Debug route to set any session variable from the debug panel
@app.route("/set_var", methods=["POST"])
def set_var():
    if not session.get('debug'):
        return "Access denied", 403
    assignment = request.form.get("assignment", "")
    if '=' in assignment:
        var, val = assignment.split('=', 1)
        var = var.strip()
        val = val.strip()
        # Try to convert to int, float, or leave as string
        try:
            if val.lower() == 'true':
                val = True
            elif val.lower() == 'false':
                val = False
            else:
                val = int(val)
        except ValueError:
            try:
                val = float(val)
            except ValueError:
                pass
        session[var] = val
        session.modified = True
    return redirect(request.referrer or "/")
def get_all_routes():
    # Returns a list of (rule, endpoint, methods)
    routes = []
    for rule in app.url_map.iter_rules():
        # Exclude static files
        if rule.endpoint != 'static':
            routes.append({
                'rule': str(rule),
                'endpoint': rule.endpoint,
                'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            })

    return routes
    
@app.route("/ping")    
def ping():
    return "", 204

# API endpoint for live idle score updates
@app.route("/idle_score")
def idle_score():
    apply_idle_income()
    return jsonify({
        'score': session.get('score', 0),
        'idle_generator': session.get('idle_generator', 0)
    })


@app.route("/", methods=["GET", "POST"])    # Set route for homepage, allow form POSTs
def select_difficulty():
    apply_idle_income()
    if 'extra_guess_total' not in session:
        session['extra_guess_total'] = 0
    if 'extra_guess_available' not in session:
        session['extra_guess_available'] = session['extra_guess_total']
    if request.method == "POST":
        difficulty = request.form.get("difficulty")
        session['difficulty'] = difficulty

        extra = session.get('extra_guess_total', 0)
        if difficulty == "easy":
            session['min_num'] = 1
            session['max_num'] = 10
            session['max_attempts'] = 3 + extra
        elif difficulty == "medium":
            session['min_num'] = 1
            session['max_num'] = 50
            session['max_attempts'] = 5 + extra
        elif difficulty == "hard":
            session['min_num'] = 1
            session['max_num'] = 100
            session['max_attempts'] = 10 + extra
        elif difficulty == "custom":
            try:
                min_num = int(request.form.get("min_num", 1))
                max_num = int(request.form.get("max_num", 100))
                base_attempts = int(request.form.get("max_attempts", 10))
                max_attempts = base_attempts + extra
                if min_num >= max_num or min_num < 1 or max_num < 1 or max_attempts < 1:
                    raise ValueError
                session["min_num"] = min_num
                session["max_num"] = max_num
                session["max_attempts"] = max_attempts
            except ValueError:
                session["min_num"] = 1
                session["max_num"] = 100
                session["max_attempts"] = 10 + extra
        else:
            session['min_num'] = 1
            session['max_num'] = 100
            session['max_attempts'] = 10 + extra

        return redirect(url_for("game"))

    return render_template("difficulty.html", all_routes=get_all_routes())



def apply_idle_income():
    # Award idle points based on time elapsed and idle_generators owned
    idle_generators = session.get('idle_generator', 0)
    if idle_generators > 0:
        now = int(time())
        last = session.get('idle_last_time', now)
        elapsed = now - last
        if elapsed > 0:
            # 1 point per generator per second
            points = elapsed * idle_generators
            if points > 0:
                session['score'] = session.get('score', 0) + points
                session['idle_last_time'] = last + elapsed
        else:
            session['idle_last_time'] = now
    else:
        session['idle_last_time'] = int(time())

@app.route("/game", methods=["GET", "POST"])    # Set route for homepage, allow form POSTs
def game():
    # Recursively convert all sets in the session to lists to avoid JSON serialization errors
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(i) for i in obj]
        else:
            return obj
    for k in list(session.keys()):
        session[k] = convert_sets(session[k])
    # Convert any sets in session to lists to avoid JSON serialization errors
    for k in list(session.keys()):
        if isinstance(session[k], set):
            session[k] = list(session[k])
    apply_idle_income()
    min_num = session.get('min_num', 1)
    max_num = session.get('max_num', 100)
    round_over = session.get('round_over', False)

    if 'correct_number' not in session:
        session['correct_number'] = randint(min_num, max_num)
        if 'score' not in session:
            session['score'] = 0
        session['attempts'] = 0
        session['log'] = []
        session['max_attempts'] = session.get('base_max_attempts', session.get('max_attempts', 10))
        # Reset available extra guesses to total at new round
        session['extra_guess_available'] = session.get('extra_guess_total', 0)
    # Achievement tracking
    if 'achievements' not in session:
        session['achievements'] = []
    # Convert old set to list if needed
    if isinstance(session['achievements'], set):
        session['achievements'] = list(session['achievements'])
    if 'correct_total' not in session:
        session['correct_total'] = 0
    # First play achievement
    ach = session.get('achievements', [])
    # Convert to list if not already
    if isinstance(ach, set):
        ach = list(ach)
    if isinstance(session['achievements'], set):
        session['achievements'] = list(session['achievements'])
    if 'First Play' not in ach:
        ach.append('First Play')
        session['achievements'] = ach

    message = ""
    # Prepare item usage flags
    hint_used = False
    multiplier_used = False

    if request.method == "POST":
        # Handle item usage
        
        if 'use_hint' in request.form and session.get('hint', 0) > 0:
            correct = session['correct_number']
            hint_type = 'even' if correct % 2 == 0 else 'odd'
            message = f"Hint: The number is {hint_type}."
            session['hint'] -= 1
            hint_used = True
        elif 'use_multiplier' in request.form and session.get('score_multiplier', 0) > 0:
            session['score_multiplier_active'] = True
            session['score_multiplier'] -= 1
            message = "Score multiplier activated for your next correct guess!"
            multiplier_used = True
        elif 'use_extra_guess' in request.form and session.get('extra_guess_available', 0) > 0:
            session['max_attempts'] = session.get('max_attempts', 10) + 1
            session['extra_guess_available'] -= 1
            message = f"Extra guess used! Max guesses this round: {session['max_attempts']}"
        elif 'next_round' in request.form:
            # User clicked "Next Round"
            session['correct_number'] = randint(min_num, max_num)
            session['attempts'] = 0
            session['log'] = []
            # Reset max_attempts to base for new round
            difficulty = session.get('difficulty', 'easy')
            if difficulty == "easy":
                base = 3
            elif difficulty == "medium":
                base = 5
            elif difficulty == "hard":
                base = 10
            elif difficulty == "custom":
                base = int(request.form.get("max_attempts", session.get('base_max_attempts', 10)))
            else:
                base = 10
            session['max_attempts'] = base
            session['base_max_attempts'] = base
            session['round_over'] = False
            session['score_multiplier_active'] = False
            # Reset available extra guesses to total at new round
            session['extra_guess_available'] = session.get('extra_guess_total', 0)
            return redirect(url_for("game"))
        else:
            guess_val = request.form.get('guess')
            try:
                if round_over:
                    message = "Click 'Next Round' to continue."
                elif guess_val is not None:
                    guess = int(guess_val)    # Get number from form
                    # Check if guess is within range
                    if guess < min_num or guess > max_num:
                        message = f"Hint: Please enter a number between {min_num} and {max_num}."
                    # Check for duplicate guess
                    elif guess in session['log']:
                        message = "Hint: You've already tried this number! Try something new."
                    else:
                        session['attempts'] += 1
                        correct = session['correct_number']

                        if guess < correct:
                            message = "Too low! Try again."
                            session['log'].append((guess, "↑"))
                        elif guess > correct:
                            message = "Too high! Try again."
                            session['log'].append((guess, "↓"))
                        else:
                            # Correct guess
                            message = f"Correct! The number was {correct}."
                            session['log'].append((guess, ""))
                            # Award points based on difficulty
                            difficulty = session.get('difficulty', 'easy')
                            multiplier = 1
                            if session.get('score_multiplier', 0) > 0:
                                multiplier = 2
                            if difficulty == "easy":
                                session['score'] += 10 * multiplier
                            elif difficulty == "medium":
                                session['score'] += 25 * multiplier
                            elif difficulty == "hard":
                                session['score'] += 50 * multiplier
                            elif difficulty == "custom":
                                max_attempts = session.get('max_attempts', 10)
                                session['score'] += int((max_num - min_num + 1) / max_attempts) * multiplier
                            message = f"Correct! The number was {correct}."
                            if multiplier > 1:
                                message += " (Score Multiplied!)"
                            session['correct_number'] = randint(min_num, max_num)   # Start new round
                            session['attempts'] = 0
                            session['log'] = []
                            round_over = True
                            # Track correct guesses
                            session['correct_total'] = session.get('correct_total', 0) + 1
                            # Achievements
                            ach = set(session.get('achievements', []))
                            # Score achievements
                            def add_ach(label, cond):
                                if cond and label not in ach:
                                    ach.append(label)
                            add_ach('Score 100', session['score'] >= 100)
                            add_ach('Score 1000', session['score'] >= 1000)
                            add_ach('Score 5000', session['score'] >= 5000)
                            add_ach('10 Correct Guesses', session['correct_total'] >= 10)
                            add_ach('50 Correct Guesses', session['correct_total'] >= 50)
                            add_ach('100 Correct Guesses', session['correct_total'] >= 100)
                            add_ach('1000 Correct Guesses', session['correct_total'] >= 1000)
                            add_ach('100 Extra Guesses Purchased', session.get('extra_guess_total', 0) >= 100)
                            add_ach('100 Hints Purchased', session.get('hint', 0) >= 100)
                            add_ach('100 Score Multipliers Purchased', session.get('score_multiplier', 0) >= 100)
                            add_ach('100 Idle Generators Purchased', session.get('idle_generator', 0) >= 100)
                            session['achievements'] = ach

                        if session['attempts'] >= session.get('max_attempts', 10):  # If too many attempts
                            # Award points based on how close the last guess was
                            difficulty = session.get('difficulty', 'easy')
                            correct = session['correct_number']
                            distance = abs(guess - correct)
                            multiplier = 1
                            if session.get('score_multiplier', 0) > 0:
                                multiplier = 2
                            if difficulty == "easy":
                                points = (10 - distance) * multiplier
                            elif difficulty == "medium":
                                points = (25 - 2 * distance) * multiplier
                            elif difficulty == "hard":
                                points = (50 - 4 * distance) * multiplier
                            elif difficulty == "custom":
                                max_num = session.get('max_num', 100)
                                min_num = session.get('min_num', 1)
                                points = int((max_num - min_num + 1) / (distance + 1)) * multiplier
                                message = f"Game over! The correct number was {correct}. You scored {points} points."
                            else:
                                points = 1 * multiplier
                            points = max(points, 0)  # Prevent negative points
                            session['score'] += points

                            message = f"Game over! The correct number was {correct}. Your last guess was {guess}. You scored {points} points this round."
                            if multiplier > 1:
                                message += " (Score Multiplied!)"
                            session['correct_number'] = randint(min_num, max_num)
                            session['attempts'] = 0
                            session['log'] = []
                            round_over = True
            except ValueError:
                message = "Please enter a valid number."


    # Final safeguard: convert all sets in session to lists before returning
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(i) for i in obj]
        else:
            return obj
    for k in list(session.keys()):
        session[k] = convert_sets(session[k])
    return render_template("index.html",    # Show page with updated info
                            message=message,
                            score=session.get('score', 0),
                            attempts=session.get('attempts', 0),
                            log=session.get('log', []),
                            min_num=min_num,
                            max_num=max_num,
                            max_attempts=session.get('max_attempts', 10),
                            round_over=session.get('round_over', False),
                            hint=session.get('hint', 0),
                            score_multiplier=session.get('score_multiplier', 0),
                            score_multiplier_active=session.get('score_multiplier_active', False),
                            extra_guess_total=session.get('extra_guess_total', 0),
                            extra_guess_available=session.get('extra_guess_available', 0),
                            achievements=session.get('achievements', []),
                            all_routes=get_all_routes())


@app.route("/shop", methods=["GET", "POST"])
def shop():
    apply_idle_income()
    score = session.get('score', 0)
    message = ""
    # Track quantities for items
    base_costs = {
        "extra_guess": 50,
        "hint": 30,
        "score_multiplier": 80,
        "idle_generator": 100
    }

    # Calculate dynamic costs based on how many of each item have been purchased
    item_costs = {}
    for item, base in base_costs.items():
        if item == "extra_guess":
            owned = session.get('extra_guess_total', 0)
        else:
            owned = session.get(item, 0)
        # Now: cost increases by 5% per item owned
        item_costs[item] = int(base * (1.05 ** owned))
    # Initialize inventory if not present
    for item in base_costs:
        if item == "extra_guess":
            if 'extra_guess_total' not in session:
                session['extra_guess_total'] = 0
            if 'extra_guess_available' not in session:
                session['extra_guess_available'] = session['extra_guess_total']
        elif item not in session:
            session[item] = 0
    # Idle generator: initialize last time if not present
    if 'idle_last_time' not in session:
        session['idle_last_time'] = int(time())

    if request.method == "POST":
        apply_idle_income()
        item = request.form.get("item")
        # Calculate cost BEFORE purchase
        cost = int(base_costs[item] * (1.15 ** session.get(item, 0))) if item in base_costs else None
        if cost and score >= cost:
            session['score'] -= cost
            if item == "extra_guess":
                session['extra_guess_total'] = session.get('extra_guess_total', 0) + 1
                session['extra_guess_available'] = session.get('extra_guess_available', 0) + 1
                message = f"You bought Extra Guess!"
                # Update max_attempts if in a round
                difficulty = session.get('difficulty', 'easy')
                extra = session.get('extra_guess_total', 0)
                if difficulty == "easy":
                    session['max_attempts'] = 3 + extra
                elif difficulty == "medium":
                    session['max_attempts'] = 5 + extra
                elif difficulty == "hard":
                    session['max_attempts'] = 10 + extra
                elif difficulty == "custom":
                    base = int(session.get('custom_base_attempts', session.get('max_attempts', 10) - extra))
                    session['max_attempts'] = base + extra
                else:
                    session['max_attempts'] = 10 + extra
            else:
                session[item] = session.get(item, 0) + 1  # Increment count
                message = f"You bought {item.replace('_', ' ').title()}!"
        else:
            message = "Not enough points or invalid item."

        # After purchase, recalculate item_costs for updated inventory
        item_costs = {}
        for item_name, base in base_costs.items():
            if item_name == "extra_guess":
                owned = session.get('extra_guess_total', 0)
            else:
                owned = session.get(item_name, 0)
            item_costs[item_name] = int(base * (1.05 ** owned))

    # Pass inventory and costs to template
    inventory = {}
    for item in base_costs:
        if item == "extra_guess":
            inventory[item] = session.get('extra_guess_total', 0)
        else:
            inventory[item] = session.get(item, 0)
    return render_template("shop.html", 
                            score=session.get('score', 0),
                            message=message,
                            inventory=inventory,
                            item_costs=item_costs,
                            all_routes=get_all_routes())

@app.route("/reset")                        #  Seperate route to clear/reset game
def reset():
    apply_idle_income()
    session.clear()                         # Remove all saved session data
    return redirect("/")                    # Go back to homepage

@app.route("/change_difficulty")
def change_difficulty():
    apply_idle_income()
    # Keep score, debug, and extra_guess, clear other session variables
    score = session.get('score', 0)
    debug = session.get('debug', False)
    extra_guess = session.get('extra_guess', 0)
    session.clear()
    session['score'] = score
    session['extra_guess'] = extra_guess
    if debug:
        session['debug'] = True
    return redirect("/")


def get_debug_key():
    try:
        with open('.debug_key') as f:
            return f.read().strip()
    except Exception:
        return None

DEBUG_KEY = get_debug_key()

@app.route("/debug")
def debug():
    secret = request.args.get("key")
    if secret == DEBUG_KEY:
        session['debug'] = True
        session.modified = True  # Ensure session is saved before redirect
        return '''
        <html>
            <head>
                <meta http-equiv="refresh" content="5;url={}">
                <script>
                    setTimeout(function() {{
                        window.location.href = "{}";
                    }}, 5000);
                </script>
            </head>
            <body>
                Debug mode activated! Redirecting in 5 seconds...
            </body>
        </html>
        '''.format(url_for("change_difficulty"), url_for("change_difficulty"))
    return "Access denied.", 403

@app.route("/disable_debug")
def disable_debug():
    if not session.get('debug'):
        return "Debug mode is not enabled.", 403
    session.pop('debug', None)
    return "Debug mode disabled."

@app.route("/set_correct_number", methods=["POST"])
def set_correct_number():
    if not session.get('debug'):
        return "Access denied", 403
    session['correct_number'] = int(request.form['correct_number'])
    return redirect("/game")

@app.route("/force_next_round", methods=["POST"])
def force_next_round():
    if not session.get('debug'):
        return "Access denied", 403
    session['attempts'] = session.get('max_attempts', 10) + 1
    return redirect("/game")

@app.route("/set_score", methods=["POST"])
def set_score():
    if not session.get('debug'):
        return "Access denied", 403
    session['score'] = int(request.form['score'])
    return redirect("/game")

@app.route("/goto_page", methods=["POST"])
def goto_page():
    if not session.get('debug'):
        return "Access denied", 403
    page = request.form.get("page", "/")
    # Only allow internal routes for safety
    if not page.startswith("/"):
        page = "/" + page
    return redirect(page)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT
    app.run(host="0.0.0.0", port=port, debug=True)
