# EduAI Academy

**EduAI Academy** is an intelligent online course platform where AI agents operate as on-demand professors — always available, always prepared, and capable of leading live sessions, answering student questions in real time, grading submissions, and moderating discussions. Think of it as autopilot for education: human instructors set the course, AI keeps it running.

Built with Django, the platform supports a full course lifecycle — enrollment, live classroom sessions, group collaboration, assignment submission, messaging, and moderation — with first-class support for both human and AI participants at every level.

---

## Tech Stack

- **Python**
- **Django**

---

## Project Structure

```
ai_academy/        # Django project config (settings, urls, wsgi, asgi)
apps/
  core/            # Shared enums and base models
  academy/         # Courses, memberships, AI agents
  accounts/        # User profiles
  ai_tools/        # AI tooling and integrations
  liveclasses/     # Classrooms and live sessions
  collaboration/   # Student groups and assignments
  communication/   # Messaging and threads
  moderation/      # Reports and moderation
```

---

## Dev Setup (GNU/Linux)

### 1. Clone the repository

```bash
git clone git@github.com:gnud/edu_ai_academy.git
cd edu_ai_academy
```

### 2. Install Python 3.12 with pyenv

If you don't have Python 3.12 installed, use [pyenv](https://github.com/pyenv/pyenv) to manage Python versions.

**Install pyenv:**

```bash
curl https://pyenv.run | bash
```

Add the following to your `~/.bashrc` or `~/.zshrc` and restart your shell:

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

**Install Python 3.12 and set it locally:**

```bash
pyenv install 3.12
pyenv local 3.12
```

This creates a `.python-version` file in the project root that pins the version for the project.

### 3. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000`.

---

## PyCharm Setup

### 1. Open the project

Open the `edu_ai_academy` directory in PyCharm.

### 2. Configure the Python interpreter

Go to **Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter**.
Select **Virtualenv Environment** and point it to the `.venv` created above,
or create a new one from the same dialog.

### 3. Mark `apps/` as a source root

Right-click the `apps/` directory in the project tree →
**Mark Directory as → Sources Root**.

This ensures imports like `from apps.core import enums` resolve correctly in the IDE.

### 4. Enable Django support

Go to **Settings → Languages & Frameworks → Django** and configure:

| Field               | Value                     |
|---------------------|---------------------------|
| Django project root | `<project root>`          |
| Settings            | `ai_academy/settings.py`  |
| Manage script       | `manage.py`               |

Click **OK**. PyCharm will now provide Django-aware code completion, template support, and ORM inspections.

### 5. Run configuration

Go to **Run → Edit Configurations → Add → Django Server**.
Leave defaults and click **Run**. The dev server will start inside PyCharm's terminal.
