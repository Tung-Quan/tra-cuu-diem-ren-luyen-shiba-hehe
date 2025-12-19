import asyncio
import httpx
import time
import random

# Configuration
API_URL = "http://localhost:8000/api/mysql/search"
NORMAL_USERS = 50       # 50 legitimate users
DDOS_ATTACKERS = 10     # 10 attackers (spamming requests)
DDOS_REQUESTS = 200     # Attackers send lots of requests
NORMAL_REQUESTS = 5     # Normal users send normal amount

def random_ip():
    return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

async def simulate_normal_user(client, user_id):
    """Simulates a normal user searching occasionally."""
    for i in range(NORMAL_REQUESTS):
        start = time.time()
        try:
            # Simulate real behavior: random delays and different queries
            await asyncio.sleep(random.uniform(0.5, 2.0))
            # Simulate unique user IP
            query = random.choice(["Nguyen", "Tran", "Le", "Pham", "Vo", "Dang"])
            headers = {"X-Forwarded-For": random_ip()}
            resp = await client.get(API_URL, params={"q": query, "limit": 10}, headers=headers)
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                print(f"[User {user_id}] ✅ OK ({elapsed:.2f}s) - {query}")
            else:
                print(f"[User {user_id}] ❌ {resp.status_code} ({elapsed:.2f}s)")
                
        except Exception as e:
            print(f"[User {user_id}] ⚠️ Error: {e}")

async def simulate_attacker(client, attacker_id):
    """Simulates a DDoS attacker spamming requests."""
    print(f"[Attacker {attacker_id}] 🚀 STARTING FLOOD!")
    success_count = 0
    blocked_count = 0
    
    for i in range(DDOS_REQUESTS):
        try:
            # Same attacker IP for all requests
            headers = {"X-Forwarded-For": f"10.0.0.{attacker_id}"}
            resp = await client.get(API_URL, params={"q": "DDOS_TEST", "limit": 50}, headers=headers)
            
            if resp.status_code == 200:
                success_count += 1
            elif resp.status_code == 429:
                blocked_count += 1
            
        except Exception:
            pass
            
    print(f"[Attacker {attacker_id}] 🛑 FINISHED. Succeeded: {success_count}, Blocked: {blocked_count}")

async def main():
    print("="*60)
    print(f"🚦 SIMULATION STARTING")
    print(f"   - {NORMAL_USERS} Normal Users (legitimate traffic)")
    print(f"   - {DDOS_ATTACKERS} Attackers (DDoS flood)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        
        # 1. Start Normal Users
        for i in range(NORMAL_USERS):
            tasks.append(simulate_normal_user(client, i))
            
        # 2. Start Attackers
        # Note: In a real test, they would have different IPs. 
        # Since we run locally, they share 1 IP, so they will trigger the limit VERY fast.
        # This proves the rate limiter protects the SYSTEM from being overwhelmed by that single IP source.
        for i in range(DDOS_ATTACKERS):
            tasks.append(simulate_attacker(client, i))
            
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
    print("\n" + "="*60)
    print(f"✅ SIMULATION COMPLETE in {total_time:.2f}s")
    print("Observations to check:")
    print("1. Normal users should ideally succeed (if they don't share IP with attackers in this test).")
    print("2. Attackers should see massive 429 Too Many Requests errors.")
    print("3. Server log should NOT show 500 errors or crashes.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
