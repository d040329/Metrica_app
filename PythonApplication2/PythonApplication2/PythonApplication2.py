import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import requests
import time
import os

class MetrikaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yandex Metrika Log Analyzer")
        self.root.geometry("1000x700")
        
        self.init_user_db()
        self.init_data_db()
        
        self.current_user = None
        self.TOKEN = None
        self.COUNTER_ID = None
        
        self.create_login_frame()
    
    def init_user_db(self):
        if not os.path.exists('metrika_users.db'):
            conn = sqlite3.connect('metrika_users.db')
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                token TEXT NOT NULL,
                counter_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            conn.commit()
            conn.close()
    
    def init_data_db(self):
        conn = sqlite3.connect('metrika_data.db')
        cursor = conn.cursor()
    
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT,
            watchID TEXT,
            goalsID TEXT,
            URL TEXT,
            lastTrafficSource TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
    
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT,
            visitID TEXT,
            counterID TEXT,
            startURL TEXT,
            pageViews INTEGER,
            visitDuration INTEGER,
            bounce INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
    
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS visit_duration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            duration INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date)
        )
        ''')
    
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            views INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date)
        )
        ''')
    
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS traffic_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date, source)
        )
        ''')
    
        conn.commit()
        conn.close()

    def create_login_frame(self):
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.login_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.login_frame, text="OAuth Token:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.token_entry = ttk.Entry(self.login_frame, show="*")
        self.token_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(self.login_frame, text="Counter ID:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.counter_id_entry = ttk.Entry(self.login_frame)
        self.counter_id_entry.grid(row=2, column=1, padx=5, pady=5)
        
        self.login_btn = ttk.Button(self.login_frame, text="Login", command=self.handle_login)
        self.login_btn.grid(row=3, column=0, padx=5, pady=10)
        
        self.register_btn = ttk.Button(self.login_frame, text="Register", command=self.handle_register)
        self.register_btn.grid(row=3, column=1, padx=5, pady=10)
        
        ttk.Label(self.login_frame, text="Or select existing user:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.user_var = tk.StringVar()
        self.user_dropdown = ttk.Combobox(self.login_frame, textvariable=self.user_var)
        self.user_dropdown.grid(row=4, column=1, padx=5, pady=5)
        
        self.load_existing_users()
        self.user_dropdown.bind("<<ComboboxSelected>>", self.user_selected)

    def load_existing_users(self):
        try:
            conn = sqlite3.connect('metrika_users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users")
            users = [row[0] for row in cursor.fetchall()]
            self.user_dropdown['values'] = users
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error loading users: {str(e)}")
        finally:
            if conn:
                conn.close()

    def user_selected(self, event):
        username = self.user_var.get()
        if not username:
            return
            
        try:
            conn = sqlite3.connect('metrika_users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT token, counter_id FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                self.token_entry.delete(0, tk.END)
                self.token_entry.insert(0, result[0])
                self.counter_id_entry.delete(0, tk.END)
                self.counter_id_entry.insert(0, result[1])
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error loading user data: {str(e)}")
        finally:
            if conn:
                conn.close()

    def handle_login(self):
        username = self.username_entry.get()
        token = self.token_entry.get()
        counter_id = self.counter_id_entry.get()
        
        if not all([username, token, counter_id]):
            messagebox.showerror("Error", "All fields are required")
            return
        
        try:
            conn = sqlite3.connect('metrika_users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, token, counter_id FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result and token == result[1] and counter_id == result[2]:
                self.current_user = result[0]
                self.TOKEN = result[1]
                self.COUNTER_ID = result[2]
                self.initialize_main_interface()
            else:
                messagebox.showerror("Error", "Invalid credentials")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error during login: {str(e)}")
        finally:
            if conn:
                conn.close()

    def handle_register(self):
        username = self.username_entry.get()
        token = self.token_entry.get()
        counter_id = self.counter_id_entry.get()

        if not all([username, token, counter_id]):
            messagebox.showerror("Error", "All fields are required")
            return

        try:
            username = self.sanitize_input(username)
            token = self.sanitize_input(token)
            counter_id = self.sanitize_input(counter_id)

            conn = sqlite3.connect('metrika_users.db')
            cursor = conn.cursor()
        
            cursor.execute("INSERT INTO users (username, token, counter_id) VALUES (?, ?, ?)", 
                         (username, token, counter_id))
            conn.commit()
        
            self.current_user = cursor.lastrowid
            self.TOKEN = token
            self.COUNTER_ID = counter_id
            self.initialize_main_interface()
            self.load_existing_users()
            messagebox.showinfo("Success", "User registered successfully")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists")
        except Exception as e:
            ()
        finally:
            if conn:
                conn.close()

    def sanitize_input(self, input_str):
        if not isinstance(input_str, str):
            input_str = str(input_str)
    
        cleaned = input_str.encode('ascii', errors='ignore').decode('ascii')
        return cleaned.strip()

    def initialize_main_interface(self):
        self.login_frame.destroy()
        
        self.url_post_hits = f'https://api-metrika.yandex.net/management/v1/counter/{self.COUNTER_ID}/logrequests'
        self.url_post_visits = f'https://api-metrika.yandex.net/management/v1/counter/{self.COUNTER_ID}/logrequests'
        
        self.headers = {
            'Authorization': f'OAuth {self.TOKEN}',
            'Content-Type': 'application/json',
        }
        
        self.request_id = 0
        self.request_id_visits = 0
        
        self.create_main_widgets()

    def create_main_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.hits_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.hits_frame, text="Hits Log")
        self.create_hits_tab()
        
        self.visits_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.visits_frame, text="Visits Log")
        self.create_visits_tab()
        
        self.db_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.db_frame, text="Database")
        self.create_db_tab()
        
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="Analytics")
        self.create_analytics_tab()
        
        self.logout_btn = ttk.Button(self.root, text="Logout", command=self.logout)
        self.logout_btn.pack(side=tk.BOTTOM, pady=5)

    def logout(self):
        self.notebook.destroy()
        self.logout_btn.destroy()
        
        self.current_user = None
        self.TOKEN = None
        self.COUNTER_ID = None
        
        self.create_login_frame()

    def create_hits_tab(self):
        ttk.Label(self.hits_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.hits_date1 = ttk.Entry(self.hits_frame)
        self.hits_date1.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.hits_frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.hits_date2 = ttk.Entry(self.hits_frame)
        self.hits_date2.grid(row=1, column=1, padx=5, pady=5)
        
        self.create_hits_btn = ttk.Button(self.hits_frame, text="Create Log Request", command=self.create_hits_request)
        self.create_hits_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.get_hits_btn = ttk.Button(self.hits_frame, text="Get Log Data", command=self.get_hits_data)
        self.get_hits_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.hits_status = ttk.Label(self.hits_frame, text="")
        self.hits_status.grid(row=4, column=0, columnspan=2, pady=5)

    def create_visits_tab(self):
        ttk.Label(self.visits_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.visits_date1 = ttk.Entry(self.visits_frame)
        self.visits_date1.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.visits_frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.visits_date2 = ttk.Entry(self.visits_frame)
        self.visits_date2.grid(row=1, column=1, padx=5, pady=5)
        
        self.create_visits_btn = ttk.Button(self.visits_frame, text="Create Log Request", command=self.create_visits_request)
        self.create_visits_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.get_visits_btn = ttk.Button(self.visits_frame, text="Get Log Data", command=self.get_visits_data)
        self.get_visits_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.visits_status = ttk.Label(self.visits_frame, text="")
        self.visits_status.grid(row=4, column=0, columnspan=2, pady=5)

    def create_db_tab(self):
        ttk.Label(self.db_frame, text="Select Table:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.table_var = tk.StringVar()
        self.table_combobox = ttk.Combobox(self.db_frame, textvariable=self.table_var, 
                                         values=["hits", "visits", "visit_duration", "page_views", "traffic_sources"])
        self.table_combobox.grid(row=0, column=1, padx=5, pady=5)
        self.table_combobox.current(0)
        
        ttk.Label(self.db_frame, text="Sort By:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.sort_var = tk.StringVar()
        self.sort_combobox = ttk.Combobox(self.db_frame, textvariable=self.sort_var)
        self.sort_combobox.grid(row=1, column=1, padx=5, pady=5)
        
        self.table_combobox.bind("<<ComboboxSelected>>", self.update_sort_fields)
        self.update_sort_fields()
        
        ttk.Label(self.db_frame, text="Limit:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.limit_var = tk.StringVar(value="10")
        self.limit_entry = ttk.Entry(self.db_frame, textvariable=self.limit_var)
        self.limit_entry.grid(row=2, column=1, padx=5, pady=5)
        
        self.load_data_btn = ttk.Button(self.db_frame, text="Load Data", command=self.load_db_data)
        self.load_data_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.clear_db_btn = ttk.Button(self.db_frame, text="Clear My Data", command=self.clear_user_data)
        self.clear_db_btn.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.db_text = scrolledtext.ScrolledText(self.db_frame, width=120, height=25)
        self.db_text.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

    def create_analytics_tab(self):
        metrics_frame = ttk.LabelFrame(self.analytics_frame, text="Visit Metrics")
        metrics_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(metrics_frame, text="Select Metric:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.metric_var = tk.StringVar()
        self.metric_combobox = ttk.Combobox(metrics_frame, textvariable=self.metric_var, 
                                          values=["visitDuration", "pageViews"])
        self.metric_combobox.grid(row=0, column=1, padx=5, pady=5)
        self.metric_combobox.current(0)
        
        self.analyze_btn = ttk.Button(metrics_frame, text="Find Max Day", command=self.find_max_day)
        self.analyze_btn.grid(row=1, column=0, columnspan=2, pady=5)
        
        self.view_all_days_btn = ttk.Button(metrics_frame, text="View All Days", command=self.view_all_days)
        self.view_all_days_btn.grid(row=2, column=0, columnspan=2, pady=5)
        
        self.analytics_text = scrolledtext.ScrolledText(self.analytics_frame, width=120, height=10)
        self.analytics_text.grid(row=1, column=0, padx=5, pady=5)
        
        traffic_frame = ttk.LabelFrame(self.analytics_frame, text="Traffic Source Search")
        traffic_frame.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(traffic_frame, text="Search Traffic Source:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.search_traffic_var = tk.StringVar()
        self.search_traffic_entry = ttk.Entry(traffic_frame, textvariable=self.search_traffic_var)
        self.search_traffic_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.search_traffic_btn = ttk.Button(traffic_frame, text="Search", command=self.search_traffic_source)
        self.search_traffic_btn.grid(row=1, column=0, columnspan=2, pady=5)
        
        self.traffic_results_text = scrolledtext.ScrolledText(self.analytics_frame, width=120, height=10)
        self.traffic_results_text.grid(row=3, column=0, padx=5, pady=5)

    def update_sort_fields(self, event=None):
        table = self.table_var.get()
        if table == "hits":
            fields = ['date', 'watchID', 'goalsID', 'URL', 'lastTrafficSource', 'created_at']
        elif table == "visits":
            fields = ['date', 'visitID', 'counterID', 'startURL', 'bounce', 'created_at']
        elif table == "visit_duration":
            fields = ['date', 'duration', 'created_at']
        elif table == "page_views":
            fields = ['date', 'views', 'created_at']
        elif table == "traffic_sources":
            fields = ['date', 'source', 'count', 'created_at']
        else:
            fields = []
        
        self.sort_combobox['values'] = fields
        if fields:
            self.sort_combobox.current(0)

    def create_hits_request(self):
        date1 = self.hits_date1.get()
        date2 = self.hits_date2.get()
        
        if not date1 or not date2:
            messagebox.showerror("Error", "Please enter both start and end dates")
            return
        
        params_hits = {
            "date1": date1,
            "date2": date2,
            "source": "hits",
            "fields": "ym:pv:date,ym:pv:watchID,ym:pv:goalsID,ym:pv:URL,ym:pv:lastTrafficSource"
        }
        
        try:
            response = requests.post(self.url_post_hits, headers=self.headers, params=params_hits)
            
            if response.status_code == 200:
                self.request_id = response.json()['log_request']['request_id']
                self.hits_status.config(text=f"Log request created. Request ID: {self.request_id}")
            else:
                messagebox.showerror("Error", f"Error: {response.status_code}, {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Request failed: {str(e)}")

    def get_hits_data(self):
        if not self.request_id:
            messagebox.showerror("Error", "Please create a log request first")
            return
        
        self.hits_status.config(text="Processing log data, please wait...")
        self.root.update()
        
        time.sleep(30)
        
        url = f'https://api-metrika.yandex.net/management/v1/counter/{self.COUNTER_ID}/logrequest/{self.request_id}/part/0/download'
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                data = lines[1:]
                
                self.save_hits_to_db(data)
                self.hits_status.config(text=f"Successfully saved {len(data)} hits records to database")
            else:
                messagebox.showerror("Error", "Log data is not ready yet. Please try again later")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get log data: {str(e)}")

    def save_hits_to_db(self, data):
        try:
            conn = sqlite3.connect('metrika_data.db')
            cursor = conn.cursor()
            
            traffic_stats = {}
            
            for line in data:
                columns = line.split()
                if len(columns) >= 5:
                    date = columns[0]
                    source = columns[4]
                    
                    cursor.execute('''
                    INSERT INTO hits (user_id, date, watchID, goalsID, URL, lastTrafficSource)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (self.current_user, date, columns[1], columns[2], columns[3], source))
                    
                    key = (date, source)
                    traffic_stats[key] = traffic_stats.get(key, 0) + 1
            
            for (date, source), count in traffic_stats.items():
                cursor.execute('''
                INSERT OR REPLACE INTO traffic_sources (user_id, date, source, count)
                VALUES (?, ?, ?, ?)
                ''', (self.current_user, date, source, count))
            
            conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error saving hits: {str(e)}")
        finally:
            if conn:
                conn.close()

    def create_visits_request(self):
        date1 = self.visits_date1.get()
        date2 = self.visits_date2.get()
        
        if not date1 or not date2:
            messagebox.showerror("Error", "Please enter both start and end dates")
            return
        
        params_visits = {
            "date1": date1,
            "date2": date2,
            "source": "visits",
            "fields": "ym:s:date,ym:s:visitID,ym:s:counterID,ym:s:startURL,ym:s:pageViews,ym:s:visitDuration,ym:s:bounce"
        }
        
        try:
            response = requests.post(self.url_post_visits, headers=self.headers, params=params_visits)
            
            if response.status_code == 200:
                self.request_id_visits = response.json()['log_request']['request_id']
                self.visits_status.config(text=f"Log request created. Request ID: {self.request_id_visits}")
            else:
                messagebox.showerror("Error", f"Error: {response.status_code}, {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Request failed: {str(e)}")

    def get_visits_data(self):
        if not self.request_id_visits:
            messagebox.showerror("Error", "Please create a log request first")
            return
        
        self.visits_status.config(text="Processing log data, please wait...")
        self.root.update()
        
        time.sleep(40)
        
        url = f'https://api-metrika.yandex.net/management/v1/counter/{self.COUNTER_ID}/logrequest/{self.request_id_visits}/part/0/download'
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                data = lines[1:]
                
                self.save_visits_to_db(data)
                self.visits_status.config(text=f"Successfully saved {len(data)} visits records to database")
            else:
                messagebox.showerror("Error", "Log data is not ready yet. Please try again later")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get log data: {str(e)}")

    def save_visits_to_db(self, data):
        try:
            conn = sqlite3.connect('metrika_data.db')
            cursor = conn.cursor()
            
            duration_stats = {}
            views_stats = {}
            
            for line in data:
                columns = line.split()
                if len(columns) >= 7:
                    date = columns[0]
                    page_views = int(columns[4])
                    visit_duration = int(columns[5])
                    
                    cursor.execute('''
                    INSERT INTO visits (user_id, date, visitID, counterID, startURL, pageViews, visitDuration, bounce)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (self.current_user, date, columns[1], columns[2], columns[3], 
                         page_views, visit_duration, int(columns[6])))
                    
                    if date in duration_stats:
                        duration_stats[date] += visit_duration
                    else:
                        duration_stats[date] = visit_duration
                    
                    if date in views_stats:
                        views_stats[date] += page_views
                    else:
                        views_stats[date] = page_views
            
            for date, duration in duration_stats.items():
                cursor.execute('''
                INSERT OR REPLACE INTO visit_duration (user_id, date, duration)
                VALUES (?, ?, ?)
                ''', (self.current_user, date, duration))
            
            for date, views in views_stats.items():
                cursor.execute('''
                INSERT OR REPLACE INTO page_views (user_id, date, views)
                VALUES (?, ?, ?)
                ''', (self.current_user, date, views))
            
            conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error saving visits: {str(e)}")
        finally:
            if conn:
                conn.close()

    def load_db_data(self):
        table = self.table_var.get()
        sort_by = self.sort_var.get()
        limit = self.limit_var.get()
        
        if not table or not sort_by or not limit:
            messagebox.showerror("Error", "Please select table, sort field and limit")
            return
        
        try:
            limit = int(limit)
        except ValueError:
            messagebox.showerror("Error", "Limit must be a number")
            return
        
        try:
            conn = sqlite3.connect('metrika_data.db')
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (self.current_user,))
            count = cursor.fetchone()[0]
            
            query = f"SELECT * FROM {table} WHERE user_id = ? ORDER BY {sort_by} DESC LIMIT {limit}"
            cursor.execute(query, (self.current_user,))
            
            self.db_text.delete(1.0, tk.END)
            self.db_text.insert(tk.END, f"Total records in {table}: {count}\n")
            self.db_text.insert(tk.END, f"Top {limit} records sorted by {sort_by} (DESC):\n\n")
            
            if table == "hits":
                headers = ["ID", "User ID", "Date", "WatchID", "GoalsID", "URL", "TrafficSource", "CreatedAt"]
            elif table == "visits":
                headers = ["ID", "User ID", "Date", "VisitID", "CounterID", "StartURL", "PageViews", "VisitDuration", "Bounce", "CreatedAt"]
            elif table == "visit_duration":
                headers = ["ID", "User ID", "Date", "Duration", "CreatedAt"]
            elif table == "page_views":
                headers = ["ID", "User ID", "Date", "Views", "CreatedAt"]
            elif table == "traffic_sources":
                headers = ["ID", "User ID", "Date", "Source", "Count", "CreatedAt"]
            else:
                headers = []
            
            self.db_text.insert(tk.END, "\t".join(headers) + "\n")
            self.db_text.insert(tk.END, "-" * 100 + "\n")
            
            for row in cursor.fetchall():
                self.db_text.insert(tk.END, "\t".join(map(str, row)) + "\n")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error loading data: {str(e)}")
        finally:
            if conn:
                conn.close()

    def search_traffic_source(self):
        search_term = self.search_traffic_var.get()
        if not search_term:
            messagebox.showerror("Error", "Please enter a search term")
            return
        
        try:
            conn = sqlite3.connect('metrika_data.db')
            cursor = conn.cursor()
            
            query = """
            SELECT * FROM traffic_sources 
            WHERE user_id = ? AND source LIKE ?
            ORDER BY count DESC
            LIMIT 100
            """
            
            cursor.execute(query, (self.current_user, f'%{search_term}%'))
            results = cursor.fetchall()
            
            self.traffic_results_text.delete(1.0, tk.END)
            
            if results:
                self.traffic_results_text.insert(tk.END, f"Found {len(results)} traffic sources containing '{search_term}':\n\n")
                
                headers = ["ID", "User ID", "Date", "Source", "Count", "CreatedAt"]
                self.traffic_results_text.insert(tk.END, "\t".join(headers) + "\n")
                self.traffic_results_text.insert(tk.END, "-" * 100 + "\n")
                
                for row in results:
                    self.traffic_results_text.insert(tk.END, "\t".join(map(str, row)) + "\n")
            else:
                self.traffic_results_text.insert(tk.END, f"No traffic sources found containing '{search_term}'")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error searching traffic sources: {str(e)}")
        finally:
            if conn:
                conn.close()

    def clear_user_data(self):
        if not messagebox.askyesno("Confirm", "Are you sure you want to clear all your data? This cannot be undone."):
            return
        
        try:
            conn = sqlite3.connect('metrika_data.db')
            cursor = conn.cursor()
            
            tables = ["hits", "visits", "visit_duration", "page_views", "traffic_sources"]
            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (self.current_user,))
            
            conn.commit()
            
            messagebox.showinfo("Success", "Your data has been cleared successfully")
            self.db_text.delete(1.0, tk.END)
            self.db_text.insert(tk.END, "Your data has been cleared\n")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error clearing data: {str(e)}")
        finally:
            if conn:
                conn.close()

    def find_max_day(self):
        metric = self.metric_var.get()
        if not metric:
            messagebox.showerror("Error", "Please select a metric")
            return
        
        try:
            conn = sqlite3.connect('metrika_data.db')
            cursor = conn.cursor()
            
            if metric == "visitDuration":
                table = "visit_duration"
                col = "duration"
            else:
                table = "page_views"
                col = "views"
            
            query = f"""
            SELECT date, {col}
            FROM {table}
            WHERE user_id = ?
            ORDER BY {col} DESC
            LIMIT 1
            """
            
            cursor.execute(query, (self.current_user,))
            result = cursor.fetchone()
            
            self.analytics_text.delete(1.0, tk.END)
            
            if result:
                self.analytics_text.insert(tk.END, f"Day with maximum {metric}:\n")
                self.analytics_text.insert(tk.END, f"Date: {result[0]}\n")
                self.analytics_text.insert(tk.END, f"Total {metric}: {result[1]}\n")
            else:
                self.analytics_text.insert(tk.END, f"No data found for {metric}")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error finding max day: {str(e)}")
        finally:
            if conn:
                conn.close()

    def view_all_days(self):
        metric = self.metric_var.get()
        if not metric:
            messagebox.showerror("Error", "Please select a metric")
            return
        
        try:
            conn = sqlite3.connect('metrika_data.db')
            cursor = conn.cursor()
            
            if metric == "visitDuration":
                table = "visit_duration"
                col = "duration"
            else:
                table = "page_views"
                col = "views"
            
            query = f"""
            SELECT date, {col}
            FROM {table}
            WHERE user_id = ?
            ORDER BY date DESC
            """
            
            cursor.execute(query, (self.current_user,))
            results = cursor.fetchall()
            
            self.analytics_text.delete(1.0, tk.END)
            
            if results:
                self.analytics_text.insert(tk.END, f"All days with {metric}:\n\n")
                self.analytics_text.insert(tk.END, "Date\t\tTotal\n")
                self.analytics_text.insert(tk.END, "-" * 30 + "\n")
                
                for row in results:
                    self.analytics_text.insert(tk.END, f"{row[0]}\t{row[1]}\n")
            else:
                self.analytics_text.insert(tk.END, f"No data found for {metric}")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error viewing all days: {str(e)}")
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = MetrikaApp(root)
    root.mainloop()