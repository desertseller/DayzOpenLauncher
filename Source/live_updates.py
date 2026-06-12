import time
import threading
from concurrent.futures import ThreadPoolExecutor

class LiveUpdater:
    def __init__(self, browser, live_info, invalidate_cb, live_info_lock=None):
        self.browser = browser
        self.live_info = live_info
        self.invalidate = invalidate_cb
        self.live_info_lock = live_info_lock
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.running = True
        self.last_queries = {}

    def query_worker(self, server):
        if not self.running:
            return False
        try:
            ip = server.get('ip')
            q_port = server.get('query_port') or server.get('port')
            if ip and q_port:
                live_data = self.browser.query_server(ip, server.get('port'), q_port)
                
                if not self.running:
                    return False
                
                if "error" not in live_data:
                    if self.live_info_lock:
                        with self.live_info_lock:
                            self.live_info[(ip, server.get('port'))] = {
                                'players': live_data.get('players'),
                                'max_players': live_data.get('max_players'),
                                'ping': live_data.get('ping'),
                                'queue': live_data.get('queue'),
                                'time': live_data.get('time'),
                                'map': live_data.get('map'),
                                'mods': live_data.get('mods', []),
                                'ts': time.time()
                            }
                    else:
                        self.live_info[(ip, server.get('port'))] = {
                            'players': live_data.get('players'),
                            'max_players': live_data.get('max_players'),
                            'ping': live_data.get('ping'),
                            'queue': live_data.get('queue'),
                            'time': live_data.get('time'),
                            'map': live_data.get('map'),
                            'mods': live_data.get('mods', []),
                            'ts': time.time()
                        }
                    return True
        except:
            pass
        return False

    def start_loop(self, get_filtered_servers_cb, get_selected_index_cb):
        def loop():
            while self.running:
                try:
                    tasks_submitted = False
                    filtered = get_filtered_servers_cb()
                    selected_idx = get_selected_index_cb()
                    
                    if filtered and selected_idx < len(filtered):
                        selected = filtered[selected_idx]
                        pass

                    subset = filtered[:30]
                    if selected_idx > 30:
                        start = max(0, selected_idx - 10)
                        end = min(len(filtered), selected_idx + 10)
                        subset.extend(filtered[start:end])

                    unique_subset = {f"{s['ip']}:{s['port']}": s for s in subset}.values()
                    
                    now = time.time()
                    if len(self.last_queries) > 1000:
                         self.last_queries = {k:v for k,v in self.last_queries.items() if now - v < 60}

                    if self.live_info_lock:
                        with self.live_info_lock:
                            if len(self.live_info) > 1000:
                                to_del = [k for k, v in self.live_info.items() if now - v.get('ts', now) > 600]
                                for k in to_del:
                                    del self.live_info[k]
                    else:
                        if len(self.live_info) > 1000:
                            to_del = [k for k, v in self.live_info.items() if now - v.get('ts', now) > 600]
                            for k in to_del:
                                del self.live_info[k]

                    for s in unique_subset:
                        key = (s.get('ip'), s.get('port'))
                        last = self.last_queries.get(key, 0)
                        
                        if now - last > 5.0:
                             self.last_queries[key] = now
                             try:
                                 self.executor.submit(self.query_worker, s)
                             except RuntimeError:
                                 break
                             tasks_submitted = True
                    
                    if tasks_submitted and self.invalidate:
                        self.invalidate()
                        
                except Exception:
                    pass
                
                time.sleep(1.0)  
        
        threading.Thread(target=loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.executor.shutdown(wait=False, cancel_futures=True)
