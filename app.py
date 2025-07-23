from flask import Flask, render_template, request, session, redirect, url_for
from random import randint
from time import sleep

app = Flask(__name__)                       # Create Flask app
app.secret_key = 'your_secret_key'          # Needed to use session data (like saving variables across pages)
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = False


@app.route("/", methods=["GET", "POST"])    # Set route for homepage, allow form POSTs
def select_difficulty():
    if request.method == "POST":
        difficulty = request.form.get("difficulty")
        session['difficulty'] = difficulty

        # Set number range and max_attempts based on difficulty
        if difficulty == "easy":
            session['min_num'] = 1
            session['max_num'] = 10
            if session['extra_guess'] > 0:
                session['max_attempts'] = 3 + session['extra_guess']
            else:
                session['max_attempts'] = 3
        elif difficulty == "medium":
            session['min_num'] = 1
            session['max_num'] = 50
            if session['extra_guess'] > 0:
                session['max_attempts'] = 5 + session['extra_guess']
            else: session['max_attempts'] = 5
        elif difficulty == "hard":
            session['min_num'] = 1
            session['max_num'] = 100
            if session['extra_guess'] > 0:
                session['max_attempts'] = 10 + session['extra_guess']
            else: session['max_attempts'] = 10
        elif difficulty == "custom":
            try:
                min_num = int(request.form.get("min_num", 1))
                max_num = int(request.form.get("max_num", 100))
                if session['extra_guess'] > 0:
                    max_attempts = int(request.form.get("max_attempts", 10)) + session['extra_guess']
                else: max_attempts = int(request.form.get("max_attempts", 10))
                # Validation
                if min_num >= max_num or min_num < 1 or max_num < 1 or max_attempts < 1:
                    raise ValueError
                session["min_num"] = min_num
                session["max_num"] = max_num
                session["max_attempts"] = max_attempts
            except ValueError:
                session["min_num"] = 1
                session["max_num"] = 100
                if session['extra_guess'] > 0:
                    session["max_attempts"] = 10 + session['extra_guess']
                else: session["max_attempts"] = 10
        else:
            session['min_num'] = 1
            session['max_num'] = 100
            if session['extra_guess'] > 0:
                session['max_attempts'] = 10 + session['extra_guess']
            else: session['max_attempts'] = 10

        return redirect(url_for("game"))
    
    return render_template("difficulty.html")


@app.route("/game", methods=["GET", "POST"])    # Set route for homepage, allow form POSTs
def game():
    min_num = session.get('min_num', 1)
    max_num = session.get('max_num', 100)
    round_over = session.get('round_over', False)

    if 'correct_number' not in session:
        session['correct_number'] = randint(min_num, max_num)
        if 'score' not in session:
            session['score'] = 0
        session['attempts'] = 0
        session['log'] = []

    message = ""

    if request.method == "POST":
        if 'next_round' in request.form:
            # User clicked "Next Round"
            session['correct_number'] = randint(min_num, max_num)
            session['attempts'] = 0
            session['log'] = []
            session['round_over'] = False
            return redirect(url_for("game"))
        try:
            if round_over:
                message = "Click 'Next Round' to continue."
            else:
                guess = int(request.form['guess'])    # Get number from form
                # Check if guess is within range
                if guess < min_num or guess > max_num:
                    message = f"Hint: Please enter a number between {min_num} and {max_num}."
                # Check for duplicate guess
                elif guess in session['log']:
                    message = "Hint: You've already tried this number! Try something new."
                else:
                    session['log'].append(guess)          # Save guess to log
                    session['attempts'] += 1
                    correct = session['correct_number']

                    if guess < correct:
                        message = "Too low! Try again."
                    elif guess > correct:
                        message = "Too high! Try again."
                    else:
                        # Award points based on difficulty
                        difficulty = session.get('difficulty', 'easy')
                        if difficulty == "easy":
                            session['score'] += 10
                        elif difficulty == "medium":
                            session['score'] += 25
                        elif difficulty == "hard":
                            session['score'] += 50
                        elif difficulty == "custom":
                            max_attempts = session.get('max_attempts', 10)
                            session['score'] += int((max_num - min_num + 1) / max_attempts)
                        message = f"Correct! The number was {correct}."
                        session['correct_number'] = randint(min_num, max_num)   # Start new round
                        session['attempts'] = 0
                        session['log'] = []
                        round_over = True

                    if session['attempts'] >= session.get('max_attempts', 10):  # If too many attempts
                        # Award points based on how close the last guess was
                        difficulty = session.get('difficulty', 'easy')
                        correct = session['correct_number']
                        distance = abs(guess - correct)
                        if difficulty == "easy":
                            points = 10 - distance
                        elif difficulty == "medium":
                            points = 25 - 2 * distance
                        elif difficulty == "hard":
                            points = 50 - 4 * distance
                        elif difficulty == "custom":
                            max_num = session.get('max_num', 100)
                            min_num = session.get('min_num', 1)
                            points = int((max_num - min_num + 1) / (distance + 1))
                            message = f"Game over! The correct number was {correct}. You scored {points} points."
                        else:
                            points = 1
                        points = max(points, 0)  # Prevent negative points
                        session['score'] += points

                        message = f"Game over! The correct number was {correct}. Your last guess was {guess}. You scored {points} points this round."
                        session['correct_number'] = randint(min_num, max_num)
                        session['attempts'] = 0
                        session['log'] = []
                        round_over = True
        except ValueError:
            message = "Please enter a valid number."


    return render_template("index.html",    # Show page with updated info
                            message=message,
                            score=session.get('score', 0),
                            attempts=session.get('attempts', 0),
                            log=session.get('log', []),
                            min_num=min_num,
                            max_num=max_num,
                            max_attempts=session.get('max_attempts', 10),
                            round_over=session.get('round_over', False))


@app.route("/shop", methods=["GET", "POST"])
def shop():
    score = session.get('score', 0)
    message = ""
    # Track quantities for items
    item_costs = {
        "extra_guess": 50,
        "reveal_range": 20,
        "hint": 30,
        "score_multiplier": 80
    }
    # Initialize inventory if not present
    for item in item_costs:
        if item not in session:
            session[item] = 0
    if request.method == "POST":
        item = request.form.get("item")
        cost = item_costs.get(item)
        if cost and score >= cost:
            session['score'] -= cost
            session[item] = session.get(item, 0) + 1  # Increment count
            message = f"You bought {item.replace('_', ' ').title()}!"
        else:
            message = "Not enough points or invalid item."
    # Pass inventory to template
    inventory = {item: session.get(item, 0) for item in item_costs}
    return render_template("shop.html", 
                            score=session.get('score', 0),
                            message=message,
                            inventory=inventory)

@app.route("/reset")                        #  Seperate route to clear/reset game
def reset():
    session.clear()                         # Remove all saved session data
    return redirect("/")                    # Go back to homepage

@app.route("/change_difficulty")
def change_difficulty():
    # Keep score and debug, clear round/session variables
    score = session.get('score', 0)
    debug = session.get('debug', False)
    session.clear()
    session['score'] = score
    if debug:
        session['debug'] = True
    return redirect("/")


@app.route("/debug")
def debug():
    secret = request.args.get("key")
    if secret == "316497":
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

if __name__ == "__main__":                  # Run app if this file is executed directly
    app.run(debug=True)                    # Enable debug mode for easier development