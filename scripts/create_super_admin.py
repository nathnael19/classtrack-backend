import sys
import os
from typing import Optional

# Add the parent directory to sys.path to allow importing from 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db import base # Ensures all models are loaded to resolve relationships
from app.models.user import User, UserRole
from app.core import security

app = typer.Typer()
console = Console()

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

@app.command()
def create_admin(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Full name of the admin"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email address for login"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Admin password"),
):
    """
    Create a new Super Admin user in the ClassTrack system.
    """
    console.print(Panel.fit("[bold blue]ClassTrack[/bold blue] - Super Admin Creation", border_style="blue"))

    if not name:
        name = Prompt.ask("[bold]Enter Admin Full Name[/bold]")
    
    if not email:
        email = Prompt.ask("[bold]Enter Admin Email[/bold]")
    
    if not password:
        password = Prompt.ask("[bold]Enter Admin Password[/bold]", password=True)

    db = get_db()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            console.print(f"[bold red]Error:[/bold red] User with email [yellow]{email}[/yellow] already exists.")
            raise typer.Exit(code=1)

        # Hash password and create user
        hashed_password = security.get_password_hash(password)
        new_admin = User(
            name=name,
            email=email,
            hashed_password=hashed_password,
            role=UserRole.admin,
            is_verified=True # Super admins are verified by default
        )

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        console.print("\n[bold green]Success![/bold green] Super Admin created successfully.")
        console.print(Panel(
            f"[bold blue]Name:[/bold blue] {new_admin.name}\n"
            f"[bold blue]Email:[/bold blue] {new_admin.email}\n"
            f"[bold blue]Role:[/bold blue] {new_admin.role.value}\n"
            f"[bold blue]Status:[/bold blue] Active & Verified",
            title="Admin Details",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {str(e)}")
        db.rollback()
        raise typer.Exit(code=1)
    finally:
        db.close()

if __name__ == "__main__":
    app()
