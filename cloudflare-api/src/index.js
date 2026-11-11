const encoder = new TextEncoder();
const TOKEN_BYTES = 32;
const SESSION_DAYS = 30;
const PBKDF2_ITERATIONS = 200000;
const EMPLOYEE_FIELDS = ["name","employee_code","department","designation","phone","email","joining_date","notes","active"];
const TASK_FIELDS = ["employee_id","task_date","title","department","details","due_time","priority","status","progress","proof_url","proof_note","submitted_at","manager_note","expose_link","target_qty","actual_qty","next_action","custom_values"];
const ATTENDANCE_FIELDS = ["attendance_status","check_in","check_out","break_minutes","attendance_note"];
const ADMIN_ROLES = new Set(["admin","developer"]);
const EMPLOYEE_ROLES = new Set(["admin","developer","hr"]);
const PRESENT_DETAIL = new Set(["present","worked","work from home","wfh","half day","late","early leave","on duty"]);

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = new Set(String(env.ALLOWED_ORIGINS || "").split(",").map(v => v.trim()).filter(Boolean));
    const headers = {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Vary": "Origin",
      ...(allowed.has(origin) ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true" } : {}),
      "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
    };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (!env.DB) return json({ error: "D1 binding is not configured" }, 503, headers);
    const url = new URL(request.url);
    try {
      if (url.pathname === "/api/health" && request.method === "GET") {
        const [employees, tasks] = await Promise.all([
          env.DB.prepare("SELECT COUNT(*) AS n FROM employees").first(),
          env.DB.prepare("SELECT COUNT(*) AS n FROM tasks").first(),
        ]);
        return json({ status: "healthy", service: "raw-strength-cloudflare-api", database_connected: true,
          total_employees: Number(employees?.n || 0), total_tasks: Number(tasks?.n || 0) }, 200, headers);
      }
      if (url.pathname === "/api/auth/login" && request.method === "POST") {
        const body = await readJson(request);
        if (!body || typeof body.username !== "string" || typeof body.password !== "string" ||
            body.username.length > 128 || body.password.length > 1024) return json({ error: "Invalid username or password" }, 400, headers);
        const user = await env.DB.prepare(
          "SELECT id, username, display_name, role, password_salt, password_hash FROM auth_users WHERE username = ? COLLATE BINARY AND active = 1"
        ).bind(body.username.trim()).first();
        if (!user || !await verifyPassword(body.password, user.password_salt, user.password_hash)) {
          return json({ error: "Invalid username or password" }, 401, headers);
        }
        const token = randomHex(TOKEN_BYTES), tokenHash = await sha256(token);
        const now = new Date(), created = now.toISOString(), expires = new Date(now.getTime() + SESSION_DAYS * 86400000).toISOString();
        await env.DB.prepare("DELETE FROM web_auth_sessions WHERE expires_at <= ?").bind(created).run();
        await env.DB.prepare("INSERT INTO web_auth_sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)")
          .bind(tokenHash, user.id, created, expires).run();
        return json({ token, user: publicUser(user) }, 200, headers);
      }
      if (url.pathname === "/api/auth/me" && request.method === "GET") {
        const activeUser = await currentUser(request, env);
        if (!activeUser) return json({ error: "Login required" }, 401, headers);
        return json({ user: activeUser }, 200, headers);
      }
      if (url.pathname === "/api/auth/logout" && request.method === "POST") {
        const token = bearer(request);
        if (!token) return json({ error: "Login required" }, 401, headers);
        const result = await env.DB.prepare("DELETE FROM web_auth_sessions WHERE token_hash = ?").bind(await sha256(token)).run();
        if (!result.success || !result.meta?.changes) return json({ error: "Login required" }, 401, headers);
        return json({ success: true }, 200, headers);
      }

      const path = url.pathname;
      if (path === "/api/auth/register" && request.method === "POST") {
        const b=await readJson(request),username=String(b.username||"").trim(),display=String(b.display_name||"").trim(),answer=normalizeAnswer(b.security_answer);
        if(!username||username.length>64||!display||display.length>100)return json({detail:"Enter a valid username and display name"},422,headers);
        if(!strongPassword(b.password))return json({detail:"Use at least 8 characters with a letter and a number"},422,headers);
        if(answer.length<2||!String(b.security_question||"").trim())return json({detail:"Choose a recovery question and enter a recovery answer"},422,headers);
        const admins=await first(env.DB,"SELECT id FROM auth_users WHERE active=1 AND role IN ('Admin','Developer') LIMIT 1");
        if(!admins)return json({detail:"An active Admin must complete initial setup before new account registration"},403,headers);
        if(await first(env.DB,"SELECT id FROM auth_users WHERE username=? COLLATE BINARY",[username]))return json({detail:"That username already exists"},409,headers);
        const ps=randomHex(16),as=randomHex(16),ph=await deriveHash(b.password,ps),ah=await deriveHash(answer,as),now=new Date().toISOString();
        await insert(env.DB,"auth_users",{username,display_name:display,role:"Staff",password_salt:ps,password_hash:ph,security_question:String(b.security_question).trim(),answer_salt:as,answer_hash:ah,active:0,created_at:now,updated_at:now});
        return json({success:true,pending_approval:true,message:"Account request submitted. An Admin must activate the account before sign-in."},200,headers);
      }
      if (path === "/api/auth/recovery-question" && request.method === "POST") {
        const b=await readJson(request),username=String(b.username||"").trim();
        let row=await first(env.DB,"SELECT security_question FROM auth_users WHERE username=? COLLATE BINARY AND active=1",[username]);
        if(!row){const matches=await all(env.DB,"SELECT security_question FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",[username]);if(matches.length===1)row=matches[0];}
        if(!row?.security_question)return json({detail:"No password-recovery question is configured for this active account. Contact an Admin."},404,headers);
        return json({security_question:row.security_question},200,headers);
      }
      if (path === "/api/auth/password-reset" && request.method === "POST") {
        const b=await readJson(request),username=String(b.username||"").trim(),answer=normalizeAnswer(b.security_answer);
        let row=await first(env.DB,"SELECT * FROM auth_users WHERE username=? COLLATE BINARY AND active=1",[username]);
        if(!row){const matches=await all(env.DB,"SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",[username]);if(matches.length===1)row=matches[0];}
        if(!row?.answer_salt||!row?.answer_hash)return json({detail:"Password recovery is unavailable for this account. Contact an Admin."},400,headers);
        if(!constantTimeEqual(await deriveHash(answer,row.answer_salt),row.answer_hash))return json({detail:"Recovery answer is incorrect"},403,headers);
        if(!strongPassword(b.new_password))return json({detail:"Use at least 8 characters with a letter and a number"},422,headers);
        const salt=randomHex(16),digest=await deriveHash(b.new_password,salt),now=new Date().toISOString();
        await env.DB.prepare("UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?").bind(salt,digest,now,row.id).run();
        await env.DB.prepare("DELETE FROM web_auth_sessions WHERE user_id=?").bind(row.id).run();
        return json({success:true,message:"Password reset successfully. Sign in with your new password."},200,headers);
      }
      if (path === "/api/auth/change-password" && request.method === "POST") {
        const b=await readJson(request),username=String(b.username||"").trim();
        let row=await first(env.DB,"SELECT * FROM auth_users WHERE username=? COLLATE BINARY AND active=1",[username]);
        if(!row){const matches=await all(env.DB,"SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",[username]);if(matches.length===1)row=matches[0];}
        if(!row)return json({detail:"No active account found for that username."},400,headers);
        if(!constantTimeEqual(await deriveHash(b.current_password||"",row.password_salt),row.password_hash))return json({detail:"Current password is incorrect."},403,headers);
        if(!strongPassword(b.new_password))return json({detail:"Use at least 8 characters, including a letter and a number."},422,headers);
        const salt=randomHex(16),digest=await deriveHash(b.new_password,salt),now=new Date().toISOString();
        await env.DB.prepare("UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?").bind(salt,digest,now,row.id).run();
        await env.DB.prepare("DELETE FROM web_auth_sessions WHERE user_id=?").bind(row.id).run();
        await audit(env.DB,{username:row.username},"Password changed",row.username);
        return json({success:true,message:"Password changed successfully. Sign in with your new password."},200,headers);
      }

      const user = await currentUser(request, env);
      if (!user) return json({ error: "Login required" }, 401, headers);
      if(path==="/api/auth/users"&&request.method==="GET"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        return json(await all(env.DB,"SELECT id,username,display_name,role,active,created_at,updated_at FROM auth_users ORDER BY username COLLATE NOCASE"),200,headers);
      }
      if(path==="/api/auth/users"&&request.method==="POST"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const b=await readJson(request),username=String(b.username||"").trim(),display=String(b.display_name||"").trim(),answer=normalizeAnswer(b.security_answer);
        const allowed=["Staff","HR","Admin","Developer"];
        if(!username||username.length>64||!display||display.length>100||!allowed.includes(b.role))return json({detail:"Enter a valid username, display name and role."},422,headers);
        if(!strongPassword(b.password)||answer.length<2||!String(b.security_question||"").trim())return json({detail:"Use a strong password and configure a recovery question and answer."},422,headers);
        if(b.role==="Developer"&&role(user)!=="developer")return forbidden(headers);
        const ps=randomHex(16),as=randomHex(16),now=new Date().toISOString();
        const id=await insert(env.DB,"auth_users",{username,display_name:display,role:b.role,password_salt:ps,password_hash:await deriveHash(b.password,ps),security_question:String(b.security_question).trim(),answer_salt:as,answer_hash:await deriveHash(answer,as),active:1,created_at:now,updated_at:now});
        await audit(env.DB,user,"User created",username+" ("+b.role+")");
        return json({success:true,id},200,headers);
      }
      const account=/^\/api\/auth\/users\/(\d+)\/(active|role|password-reset)$/.exec(path);
      if(account){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const id=Number(account[1]),action=account[2],target=await first(env.DB,"SELECT id,username,role,active FROM auth_users WHERE id=?",[id]);
        if(!target)return json({detail:"Account not found"},404,headers);
        if(target.role==="Developer"&&role(user)!=="developer")return forbidden(headers);
        const b=await readJson(request);
        if(action==="active"&&request.method==="PATCH"){
          const active=!!b.active;
          if(Number(user.id)===id&&!active)return json({detail:"You cannot deactivate your own account"},400,headers);
          if(!active&&target.role==="Admin"){const count=await first(env.DB,"SELECT COUNT(*) AS n FROM auth_users WHERE active=1 AND role='Admin' AND id<>?",[id]);if(Number(count?.n||0)<1)return json({detail:"The last active Admin account cannot be deactivated"},409,headers);}
          await env.DB.prepare("UPDATE auth_users SET active=?,updated_at=? WHERE id=?").bind(active?1:0,new Date().toISOString(),id).run();
          if(!active)await env.DB.prepare("DELETE FROM web_auth_sessions WHERE user_id=?").bind(id).run();
          await audit(env.DB,user,"User status changed",target.username+": "+(active?"Active":"Disabled"));
          return json({success:true,user_id:id,active},200,headers);
        }
        if(action==="role"&&request.method==="PATCH"){
          const next=String(b.role||"");if(!["Staff","HR","Admin","Developer"].includes(next))return json({detail:"Select a valid account role"},422,headers);
          if((target.role==="Developer"||next==="Developer")&&role(user)!=="developer")return forbidden(headers);
          if(target.role==="Admin"&&next!=="Admin"&&target.active){const count=await first(env.DB,"SELECT COUNT(*) AS n FROM auth_users WHERE active=1 AND role='Admin' AND id<>?",[id]);if(Number(count?.n||0)<1)return json({detail:"The last active Admin cannot be changed to a non-Admin role"},409,headers);}
          await env.DB.prepare("UPDATE auth_users SET role=?,updated_at=? WHERE id=?").bind(next,new Date().toISOString(),id).run();
          await env.DB.prepare("DELETE FROM web_auth_sessions WHERE user_id=?").bind(id).run();
          await audit(env.DB,user,"User role changed",target.username+" -> "+next);
          return json({success:true,user_id:id,role:next},200,headers);
        }
        if(action==="password-reset"&&request.method==="POST"){
          if(!strongPassword(b.new_password))return json({detail:"Use at least 8 characters with a letter and a number"},422,headers);
          const salt=randomHex(16),digest=await deriveHash(b.new_password,salt);
          await env.DB.prepare("UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?").bind(salt,digest,new Date().toISOString(),id).run();
          await env.DB.prepare("DELETE FROM web_auth_sessions WHERE user_id=?").bind(id).run();
          await audit(env.DB,user,"User password reset by admin",target.username);
          return json({success:true,user_id:id,message:"Password reset successfully. The account must sign in again."},200,headers);
        }
      }
      if (path === "/api/employees" && request.method === "GET") {
        const where = ["1=1"], args = [];
        if (url.searchParams.get("active_only") !== "false") where.push("active=1");
        if (url.searchParams.get("department")) { where.push("department=?"); args.push(url.searchParams.get("department")); }
        if (url.searchParams.get("search")) {
          where.push("(name LIKE ? OR employee_code LIKE ? OR designation LIKE ? OR department LIKE ? OR phone LIKE ? OR email LIKE ?)");
          const term = "%" + url.searchParams.get("search").trim() + "%"; args.push(term,term,term,term,term,term);
        }
        const rows = await all(env.DB, "SELECT * FROM employees WHERE " + where.join(" AND ") + " ORDER BY active DESC,display_order ASC,name COLLATE NOCASE,id ASC", args);
        return json(rows, 200, headers);
      }
      if (path === "/api/employees" && request.method === "POST") {
        if (!EMPLOYEE_ROLES.has(role(user))) return forbidden(headers);
        const b = await readJson(request), name = String(b.name || "").trim(), email = String(b.email || "").trim();
        if (!name) return json({detail:"Employee name is required."},422,headers);
        if (email && (!email.includes("@") || !email.split("@").at(-1).includes("."))) return json({detail:"Enter a valid email address or leave it blank."},422,headers);
        const code = String(b.employee_code || "").trim() || "EMP" + randomHex(2).toUpperCase(), now = new Date().toISOString();
        const values = {name,employee_code:code,department:String(b.department||"").trim(),designation:String(b.designation||"").trim(),phone:String(b.phone||"").trim(),email,joining_date:String(b.joining_date||"").trim(),notes:String(b.notes||"").trim(),active:b.active === false || b.active === 0 ? 0 : 1,created_at:now};
        const id = await insert(env.DB,"employees",values);
        await ensureGroup(env.DB, values.department, now);
        return json({id,success:true,employee_code:code},200,headers);
      }
      const emp = /^\/api\/employees\/(\d+)$/.exec(path);
      if (emp && request.method === "PUT") {
        if (!EMPLOYEE_ROLES.has(role(user))) return forbidden(headers);
        const id=Number(emp[1]), b=await readJson(request), old=await first(env.DB,"SELECT employee_code FROM employees WHERE id=?",[id]);
        if(!old)return json({detail:"Employee not found"},404,headers);
        const name=String(b.name||"").trim(),email=String(b.email||"").trim();
        if(!name)return json({detail:"Employee name is required."},422,headers);
        if(email&&(!email.includes("@")||!email.split("@").at(-1).includes(".")))return json({detail:"Enter a valid email address or leave it blank."},422,headers);
        const v={name,employee_code:String(b.employee_code||"").trim()||old.employee_code,department:String(b.department||"").trim(),designation:String(b.designation||"").trim(),phone:String(b.phone||"").trim(),email,joining_date:String(b.joining_date||"").trim(),notes:String(b.notes||"").trim(),active:b.active===false||b.active===0?0:1};
        await update(env.DB,"employees",v,id); await ensureGroup(env.DB,v.department,new Date().toISOString());
        return json({success:true},200,headers);
      }
      if (emp && request.method === "DELETE") {
        if (!EMPLOYEE_ROLES.has(role(user))) return forbidden(headers);
        const id=Number(emp[1]), old=await first(env.DB,"SELECT active FROM employees WHERE id=?",[id]);
        if(!old)return json({detail:"Employee not found"},404,headers);
        await env.DB.prepare("UPDATE employees SET active=? WHERE id=?").bind(old.active?0:1,id).run();
        return json({success:true,active:old.active?0:1},200,headers);
      }

      if (path === "/api/tasks" && request.method === "GET") {
        const where=["1=1"],args=[];
        for(const key of ["employee_id","task_date","status","priority","department"]) if(url.searchParams.has(key)){where.push("t."+key+"=?");args.push(url.searchParams.get(key));}
        const rows=await all(env.DB,"SELECT t.*,e.name AS employee_name,e.employee_code FROM tasks t LEFT JOIN employees e ON t.employee_id=e.id WHERE "+where.join(" AND ")+" ORDER BY t.task_date DESC,t.id DESC",args);
        for(const row of rows){try{const x=JSON.parse(row.custom_values||"[]");row.custom_fields=Array.isArray(x)?x:Object.entries(x).map(([key,value])=>({key,value}));}catch{row.custom_fields=[];}}
        return json(rows,200,headers);
      }
      if (path === "/api/tasks" && request.method === "POST") {
        const b=await readJson(request),v=taskValues(b),now=new Date().toISOString();
        if(!v.title)return json({detail:"Task title is required."},422,headers);
        if(!validDate(v.task_date))return json({detail:"Task date must use YYYY-MM-DD format."},422,headers);
        if(v.progress<0||v.progress>100)return json({detail:"Task progress must be between 0 and 100."},422,headers);
        if(v.status==="Completed")v.progress=100;
        v.submitted_at=["Submitted","Completed"].includes(v.status)?now:"";
        v.created_at=now;v.updated_at=now;
        const id=await insert(env.DB,"tasks",v);
        if(b.target_qty!==undefined||b.actual_qty!==undefined) await upsertTarget(env.DB,v.employee_id,v.task_date,v.target_qty,v.actual_qty,now);
        return json({id,success:true,status:v.status,progress:v.progress,submitted_at:v.submitted_at},200,headers);
      }
      const task=/^\/api\/tasks\/(\d+)$/.exec(path);
      if(task&&request.method==="PUT"){
        const id=Number(task[1]),b=await readJson(request),old=await first(env.DB,"SELECT * FROM tasks WHERE id=?",[id]);
        if(!old)return json({detail:"Task not found."},404,headers);
        const v=taskValues(b);
        if(!v.title)return json({detail:"Task title is required."},422,headers);
        if(!validDate(v.task_date))return json({detail:"Task date must use YYYY-MM-DD format."},422,headers);
        v.target_qty=b.target_qty===undefined?(old.target_qty||""):v.target_qty;
        v.actual_qty=b.actual_qty===undefined?(old.actual_qty||""):v.actual_qty;
        if(v.status==="Completed")v.progress=100;
        v.submitted_at=old.submitted_at||(["Submitted","Completed"].includes(v.status)?new Date().toISOString():"");
        v.updated_at=new Date().toISOString();
        delete v.created_at; await update(env.DB,"tasks",v,id);
        if(b.target_qty!==undefined||b.actual_qty!==undefined)await upsertTarget(env.DB,v.employee_id,v.task_date,v.target_qty,v.actual_qty,v.updated_at);
        return json({id,success:true,status:v.status,progress:v.progress,submitted_at:v.submitted_at},200,headers);
      }
      if(path==="/api/tasks/bulk-edit"&&request.method==="POST"){
        const b=await readJson(request),ids=[...new Set((b.task_ids||[]).map(Number))],updates=b.updates||{};
        const allowed=new Set(["title","department","details","due_time","priority","status","progress","target_qty","actual_qty","next_action","proof_url","proof_note","manager_note","expose_link","custom_values"]);
        if(!ids.length||ids.length>500||!Object.keys(updates).length||Object.keys(updates).some(k=>!allowed.has(k)))return json({detail:"Invalid bulk task selection or fields."},422,headers);
        if(updates.title!==undefined&&!String(updates.title).trim())return json({detail:"Task title cannot be blank."},422,headers);
        if(updates.progress!==undefined&&(Number(updates.progress)<0||Number(updates.progress)>100))return json({detail:"Task progress must be between 0 and 100."},422,headers);
        if(updates.status==="Completed")updates.progress=100;
        if(updates.custom_values!==undefined&&typeof updates.custom_values!=="string")updates.custom_values=JSON.stringify(updates.custom_values);
        if(updates.expose_link!==undefined)updates.expose_link=updates.expose_link?1:0;
        if(updates.next_action!==undefined&&updates.manager_note===undefined)updates.manager_note=updates.next_action;
        if(updates.manager_note!==undefined&&updates.next_action===undefined)updates.next_action=updates.manager_note;
        const rows=await all(env.DB,"SELECT id,submitted_at FROM tasks WHERE id IN ("+ids.map(()=>"?").join(",")+")",ids);
        if(rows.length!==ids.length)return json({detail:"One or more selected tasks no longer exist."},404,headers);
        const now=new Date().toISOString();
        for(const row of rows){const v={...updates,updated_at:now};if(v.status&&["Submitted","Completed"].includes(v.status)&&!row.submitted_at)v.submitted_at=now;await update(env.DB,"tasks",v,row.id);}
        return json({success:true,updated:rows.length},200,headers);
      }
      if(task&&request.method==="DELETE"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const result=await env.DB.prepare("DELETE FROM tasks WHERE id=?").bind(Number(task[1])).run();
        return json({success:!!result.meta?.changes},200,headers);
      }
      if(path==="/api/employee-targets"&&request.method==="GET"){
        const id=Number(url.searchParams.get("employee_id")),date=url.searchParams.get("target_date");
        if(!id||!validDate(date))return json({detail:"employee_id and valid target_date are required."},422,headers);
        const row=await first(env.DB,"SELECT target,target_status FROM employee_targets WHERE employee_id=? AND target_date=?",[id,date]);
        return json({employee_id:id,target_date:date,target:row?.target||"",target_status:row?.target_status||""},200,headers);
      }

      if(path==="/api/attendance"&&request.method==="GET"){
        const date=url.searchParams.get("work_date")||new Date().toISOString().slice(0,10);
        if(!validDate(date))return json({detail:"work_date must use YYYY-MM-DD format"},422,headers);
        const roster=await all(env.DB,"SELECT e.id AS employee_id,e.name,e.employee_code,e.department,e.designation,COALESCE(a.attendance_status,'Unmarked') AS attendance_status,COALESCE(a.check_in,'') AS check_in,COALESCE(a.check_out,'') AS check_out,COALESCE(a.break_minutes,0) AS break_minutes,COALESCE(a.attendance_note,'') AS attendance_note,a.updated_at FROM employees e LEFT JOIN attendance a ON e.id=a.employee_id AND a.work_date=? WHERE e.active=1 ORDER BY e.display_order ASC,e.name COLLATE NOCASE",[date]);
        return json({date,roster,remarks_options:[]},200,headers);
      }
      if(path==="/api/attendance/mark"&&request.method==="POST"){
        const b=await readJson(request),date=b.work_date||new Date().toISOString().slice(0,10),id=Number(b.employee_id);
        if(!id||!validDate(date))return json({detail:"employee_id and valid work_date are required."},422,headers);
        if(await first(env.DB,"SELECT holiday_name FROM holidays WHERE holiday_date=?",[date]))return json({detail:"This date is declared as a holiday. Remove the holiday declaration before recording attendance."},409,headers);
        const old=await first(env.DB,"SELECT * FROM attendance WHERE employee_id=? AND work_date=?",[id,date]);
        let status=String(b.status||b.attendance_status||"Present").trim();
        if(["present","absent","leave","unmarked"].includes(status.toLowerCase()))status=status[0].toUpperCase()+status.slice(1).toLowerCase();
        else if(!PRESENT_DETAIL.has(status.toLowerCase()))return json({detail:"Invalid attendance status."},422,headers);
        const checkIn=b.check_in===undefined?(old?.check_in||""):String(b.check_in||"").trim();
        const checkOut=b.check_out===undefined?(old?.check_out||""):String(b.check_out||"").trim();
        const note=b.notes===undefined?(b.attendance_note===undefined?(old?.attendance_note||""):b.attendance_note):b.notes;
        const breakMinutes=b.break_minutes===undefined?Number(old?.break_minutes||0):Math.max(0,Number(b.break_minutes||0));
        if((checkIn&&!validTime(checkIn))||(checkOut&&!validTime(checkOut)))return json({detail:"Check-in and check-out must use 24-hour HH:MM format."},422,headers);
        if(["Absent","Leave","Unmarked"].includes(status)){if(checkIn||checkOut)return json({detail:"Absent, Leave and Unmarked cannot have check-in/out times."},422,headers);}
        if(checkOut&&!checkIn)return json({detail:"Check-out requires a check-in"},422,headers);
        const now=new Date().toISOString();
        await env.DB.prepare("INSERT INTO attendance(employee_id,work_date,attendance_status,check_in,check_out,break_minutes,attendance_note,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(employee_id,work_date) DO UPDATE SET attendance_status=excluded.attendance_status,check_in=excluded.check_in,check_out=excluded.check_out,break_minutes=excluded.break_minutes,attendance_note=excluded.attendance_note,updated_at=excluded.updated_at").bind(id,date,status,checkIn,checkOut,breakMinutes,String(note||""),now).run();
        return json({success:true,attendance:await first(env.DB,"SELECT * FROM attendance WHERE employee_id=? AND work_date=?",[id,date])},200,headers);
      }

      if(path==="/api/attendance/bulk-edit"&&request.method==="POST"){
        const b=await readJson(request),date=b.work_date,ids=[...new Set((b.employee_ids||[]).map(Number).filter(n=>Number.isInteger(n)&&n>0))];
        if(!validDate(date))return json({detail:"work_date must use YYYY-MM-DD format"},422,headers);
        if(!ids.length||ids.length>1000)return json({detail:"Select between 1 and 1000 employees."},422,headers);
        if(![b.apply_status,b.apply_check_in,b.apply_check_out,b.apply_remarks].some(Boolean))return json({detail:"Select at least one field to apply."},422,headers);
        const statusMap={present:"Present",absent:"Absent",leave:"Leave",unmarked:"Unmarked"};
        if(b.apply_status&&!statusMap[String(b.status||"").toLowerCase()])return json({detail:"Attendance status must be Present, Absent, Leave or Unmarked."},422,headers);
        if(b.apply_check_in&&b.check_in&&!validTime(b.check_in))return json({detail:"Check-in must use 24-hour HH:MM format."},422,headers);
        if(b.apply_check_out&&b.check_out&&!validTime(b.check_out))return json({detail:"Check-out must use 24-hour HH:MM format."},422,headers);
        if(await first(env.DB,"SELECT holiday_name FROM holidays WHERE holiday_date=?",[date]))return json({detail:"This date is declared as a holiday. Remove the holiday declaration before editing attendance."},409,headers);
        const employees=await all(env.DB,"SELECT id FROM employees WHERE active=1 AND id IN ("+ids.map(()=>"?").join(",")+")",ids);
        if(employees.length!==ids.length)return json({detail:"One or more selected active employees were not found."},404,headers);
        let updated=0;const now=new Date().toISOString();
        for(const id of ids){
          const old=await first(env.DB,"SELECT * FROM attendance WHERE employee_id=? AND work_date=?",[id,date]);
          let status=b.apply_status?statusMap[String(b.status).toLowerCase()]:(old?.attendance_status||"Unmarked");
          let checkIn=b.apply_check_in?String(b.check_in||"").trim():(old?.check_in||"");
          let checkOut=b.apply_check_out?String(b.check_out||"").trim():(old?.check_out||"");
          const remarks=b.apply_remarks?String(b.remarks||""):(old?.attendance_note||"");
          if(["Absent","Leave","Unmarked"].includes(status)){checkIn="";checkOut="";}
          else if((checkIn||checkOut)&&!PRESENT_DETAIL.has(status.toLowerCase()))status="Present";
          if(checkOut&&!checkIn)return json({detail:"Check-out requires a check-in."},422,headers);
          await env.DB.prepare("INSERT INTO attendance(employee_id,work_date,attendance_status,check_in,check_out,break_minutes,attendance_note,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(employee_id,work_date) DO UPDATE SET attendance_status=excluded.attendance_status,check_in=excluded.check_in,check_out=excluded.check_out,break_minutes=excluded.break_minutes,attendance_note=excluded.attendance_note,updated_at=excluded.updated_at").bind(id,date,status,checkIn,checkOut,Number(old?.break_minutes||0),remarks,now).run();
          updated++;
        }
        return json({success:true,updated},200,headers);
      }
      if(path==="/api/attendance/summary"&&request.method==="GET"){
        const selected=url.searchParams.get("work_date")||new Date().toISOString().slice(0,10);
        if(!validDate(selected))return json({detail:"work_date must use YYYY-MM-DD format"},422,headers);
        const monthStart=selected.slice(0,7)+"-01",today=new Date().toISOString().slice(0,10),end=selected<today?selected:today;
        const employees=await all(env.DB,"SELECT id,name,joining_date FROM employees WHERE active=1 ORDER BY name COLLATE NOCASE");
        if(!employees.length)return json({date:selected,month_start:monthStart,through_date:end,rows:[]},200,headers);
        const ids=employees.map(e=>Number(e.id)),marks=ids.map(()=>"?").join(",");
        const [tasks,attendance,holidays,setting]=await Promise.all([
          all(env.DB,"SELECT employee_id,MIN(task_date) AS first_day FROM tasks WHERE employee_id IN ("+marks+") AND task_date<>'' GROUP BY employee_id",ids),
          all(env.DB,"SELECT employee_id,work_date,attendance_status,check_in FROM attendance WHERE employee_id IN ("+marks+") AND work_date<=? ORDER BY employee_id,work_date",[...ids,end]),
          all(env.DB,"SELECT holiday_date FROM holidays WHERE holiday_date<=?",[end]),
          first(env.DB,"SELECT value FROM settings WHERE key='working_weekdays'")
        ]);
        const firstTask=new Map(tasks.map(r=>[Number(r.employee_id),r.first_day]));
        const attBy=new Map(ids.map(id=>[id,[]]));for(const r of attendance)attBy.get(Number(r.employee_id)).push(r);
        const holidaySet=new Set(holidays.map(h=>h.holiday_date)),weekdays=new Set(normalizeWeekdays(setting?.value));
        const rows=[];
        for(const emp of employees){
          const id=Number(emp.id);let start=validDate(emp.joining_date)?emp.joining_date:firstTask.get(id);
          if(!validDate(start)){const earliest=attBy.get(id).map(r=>r.work_date).filter(validDate).sort()[0];start=earliest||today;}
          const effective=start>monthStart?start:monthStart;
          let work=0,holidayCount=0,present=0,absent=0,leave=0,totalPresent=0;
          const monthly=[];
          if(effective<=end){
            for(let d=effective;d<=end;d=addDays(d,1)){const dow=((new Date(d+"T00:00:00Z").getUTCDay()+6)%7);if(weekdays.has(dow)&&!holidaySet.has(d)){work++;}}
            for(const h of holidaySet){if(h>=effective&&h<=end&&weekdays.has(((new Date(h+"T00:00:00Z").getUTCDay()+6)%7)))holidayCount++;}
            for(const a of attBy.get(id)){const dow=((new Date(a.work_date+"T00:00:00Z").getUTCDay()+6)%7);if(a.work_date<start||!weekdays.has(dow)||holidaySet.has(a.work_date))continue;const st=String(a.attendance_status||"").trim().toLowerCase(),isPresent=PRESENT_DETAIL.has(st)||(["","unmarked"].includes(st)&&!!String(a.check_in||"").trim());if(isPresent)totalPresent++;if(a.work_date>=effective){monthly.push(a);if(isPresent)present++;if(st==="absent")absent++;if(st==="leave")leave++;}}
          }
          rows.push({employee_id:id,employee_name:emp.name,start_date:start,work_days:work,present,absent,leave,holidays:holidayCount,total_present:totalPresent});
        }
        return json({date:selected,month_start:monthStart,through_date:end,rows},200,headers);
      }

      if(path==="/api/holidays"&&request.method==="GET")return json(await all(env.DB,"SELECT holiday_date,holiday_name,created_at FROM holidays ORDER BY holiday_date ASC"),200,headers);
      if(path==="/api/holidays"&&request.method==="POST"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const b=await readJson(request),date=b.holiday_date,name=String(b.holiday_name||"").trim();
        if(!validDate(date)||!name)return json({detail:"A valid holiday date and name are required."},422,headers);
        if(await first(env.DB,"SELECT holiday_name FROM holidays WHERE holiday_date=?",[date]))return json({detail:"Holiday already declared."},409,headers);
        await env.DB.prepare("INSERT INTO holidays(holiday_date,holiday_name,created_at) VALUES(?,?,?)").bind(date,name,new Date().toISOString()).run();
        await audit(env.DB,user,"Holiday declared",date+": "+name);
        return json({success:true},200,headers);
      }
      const holiday=/^\/api\/holidays\/(\d{4}-\d{2}-\d{2})$/.exec(path);
      if(holiday&&request.method==="DELETE"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        await env.DB.prepare("DELETE FROM holidays WHERE holiday_date=?").bind(holiday[1]).run();
        return json({success:true},200,headers);
      }

      if(path==="/api/settings/working-weekdays"&&request.method==="GET"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const row=await first(env.DB,"SELECT value FROM settings WHERE key='working_weekdays'");
        return json({weekdays:normalizeWeekdays(row?.value),sunday_required:true},200,headers);
      }
      if(path==="/api/settings/working-weekdays"&&request.method==="PUT"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const b=await readJson(request),days=[...new Set((b.weekdays||[]).map(Number).filter(n=>Number.isInteger(n)&&n>=0&&n<=6).concat([6]))].sort();
        if(!days.length)return json({detail:"Choose valid weekdays."},422,headers);
        await env.DB.prepare("INSERT INTO settings(key,value) VALUES('working_weekdays',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(days.join(",")).run();
        await audit(env.DB,user,"Working week changed",days.join(","));
        return json({success:true,weekdays:days,sunday_required:true},200,headers);
      }
      if(path==="/api/settings"&&request.method==="GET"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const rows=await all(env.DB,"SELECT key,value FROM settings");
        return json({settings:Object.fromEntries(rows.map(r=>[r.key,r.value])),app_version:"1.3.82",app_name:"Raw Strength Calisthenics — Employee Audit Manager"},200,headers);
      }
      if(path==="/api/settings"&&request.method==="POST"){
        if(!ADMIN_ROLES.has(role(user)))return forbidden(headers);
        const b=await readJson(request);
        for(const [key,value] of Object.entries(b))await env.DB.prepare("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(key,String(value)).run();
        return json({success:true},200,headers);
      }


      if(path==="/api/business/orders"&&request.method==="POST"){
        const b=await readJson(request),code=String(b.order_code||"").trim()||"WEB-"+randomHex(3).toUpperCase(),date=b.order_date||new Date().toISOString().slice(0,10),status=String(b.status||"Pending");
        const allowed=["Pending","Confirmed","Packed","Dispatched","Delivered","Completed","Cancelled","Returned"];
        const value=Number(b.order_value||0),discount=Number(b.discount||0);
        if(!validDate(date)||!allowed.includes(status)||!Number.isFinite(value)||value<0||!Number.isFinite(discount)||discount<0)return json({detail:"Invalid order date, status, value or discount."},422,headers);
        if(b.assigned_employee_id!==undefined&&b.assigned_employee_id!==null&&!await first(env.DB,"SELECT id FROM employees WHERE id=? AND active=1",[Number(b.assigned_employee_id)]))return json({detail:"Assigned employee was not found or is inactive."},400,headers);
        const now=new Date().toISOString();
        const id=await insert(env.DB,"bt_orders",{external_order_id:code,order_date:date,sales_channel:String(b.channel||""),customer_name:String(b.customer_name||"").trim(),contact:String(b.contact||""),payment_mode:String(b.payment_mode||""),order_status:status,discount,order_value:value,invoice_number:String(b.invoice_number||""),shipment_id:String(b.shipment_id||""),assigned_employee_id:b.assigned_employee_id||null,updated_by:user.username,updated_at:now,remarks:String(b.notes||"")});
        return json({success:true,id,order_code:code},200,headers);
      }
      const order=/^\/api\/business\/orders\/(\d+)$/.exec(path);
      if(order&&request.method==="PATCH"){
        const b=await readJson(request),status=String(b.status||"");
        if(!["Pending","Confirmed","Packed","Dispatched","Delivered","Completed","Cancelled","Returned"].includes(status))return json({detail:"Invalid order status."},400,headers);
        const r=await env.DB.prepare("UPDATE bt_orders SET order_status=?,updated_by=?,updated_at=? WHERE id=?").bind(status,user.username,new Date().toISOString(),Number(order[1])).run();
        if(!r.meta?.changes)return json({detail:"Order not found."},404,headers);
        return json({success:true},200,headers);
      }
      if(path==="/api/business/members"&&request.method==="POST"){
        const b=await readJson(request),name=String(b.full_name||"").trim();
        if(!name)return json({detail:"Member name is required."},422,headers);
        const purchased=Number(b.sessions_purchased||0),completed=Number(b.sessions_completed||0);
        if(purchased<0||completed<0||!Number.isInteger(purchased)||!Number.isInteger(completed))return json({detail:"Session counts cannot be negative."},422,headers);
        let serviceId=b.service_id??null;
        if(serviceId===null&&String(b.plan_name||"").trim()){const found=await first(env.DB,"SELECT id FROM bt_services WHERE name=? COLLATE NOCASE LIMIT 1",[String(b.plan_name).trim()]);serviceId=found?.id??null;}
        if(serviceId!==null&&!await first(env.DB,"SELECT id FROM bt_services WHERE id=?",[serviceId]))return json({detail:"Selected service was not found."},400,headers);
        if(b.assigned_trainer_id!==undefined&&b.assigned_trainer_id!==null&&!await first(env.DB,"SELECT id FROM employees WHERE id=? AND active=1",[b.assigned_trainer_id]))return json({detail:"Assigned trainer was not found or is inactive."},400,headers);
        const registration=b.registration_date||b.start_date||new Date().toISOString().slice(0,10),start=b.start_date||registration,end=b.end_date||"";
        if(!validDate(registration)||!validDate(start)||(end&&!validDate(end)))return json({detail:"Membership dates must use YYYY-MM-DD."},422,headers);
        if(!["Active","Expired","Inactive","Cancelled","Suspended"].includes(b.status||"Active")||!["Pending","Paid","Partial","Overdue","Refunded"].includes(b.payment_status||"Pending"))return json({detail:"Invalid membership or payment status."},422,headers);
        const id=await insert(env.DB,"bt_members",{name,contact:String(b.phone||""),service_id:serviceId,training_mode:String(b.training_mode||""),registration_date:registration,start_date:start,expiry_date:end,sessions_purchased:purchased,sessions_completed:completed,assigned_trainer_id:b.assigned_trainer_id||null,status:b.status||"Active",payment_status:b.payment_status||"Pending",invoice_ref:String(b.invoice_ref||""),remarks:String(b.notes||"")});
        return json({success:true,id},200,headers);
      }
      const member=/^\/api\/business\/members\/(\d+)$/.exec(path);
      if(member&&request.method==="PATCH"){
        const b=await readJson(request),map={status:"status",payment_status:"payment_status",sessions_purchased:"sessions_purchased",sessions_completed:"sessions_completed",end_date:"expiry_date",invoice_ref:"invoice_ref",notes:"remarks"},v={};
        for(const [key,col] of Object.entries(map))if(b[key]!==undefined)v[col]=b[key];
        if(!Object.keys(v).length)return json({detail:"No membership changes were supplied."},422,headers);
        if(v.status!==undefined&&!["Active","Expired","Inactive","Cancelled","Suspended"].includes(v.status))return json({detail:"Invalid membership status."},422,headers);
        if(v.payment_status!==undefined&&!["Pending","Paid","Partial","Overdue","Refunded"].includes(v.payment_status))return json({detail:"Invalid payment status."},422,headers);
        for(const k of ["sessions_purchased","sessions_completed"])if(v[k]!==undefined&&(!Number.isInteger(Number(v[k]))||Number(v[k])<0))return json({detail:"Session counts cannot be negative."},422,headers);
        if(v.expiry_date&&!validDate(v.expiry_date))return json({detail:"End date must use YYYY-MM-DD."},422,headers);
        const old=await first(env.DB,"SELECT id FROM bt_members WHERE id=?",[Number(member[1])]);if(!old)return json({detail:"Member not found."},404,headers);
        await update(env.DB,"bt_members",v,Number(member[1]));return json({success:true},200,headers);
      }
      if(path==="/api/business/activities"&&request.method==="POST"){
        const b=await readJson(request),employee=Number(b.employee_id),quantity=Number(b.quantity||0),status=b.task_status||"Pending";
        if(!await first(env.DB,"SELECT id FROM employees WHERE id=? AND active=1",[employee]))return json({detail:"Select an active employee."},400,headers);
        if(!Number.isFinite(quantity)||quantity<0||!["Pending","In Progress","Completed","Blocked","Cancelled"].includes(status))return json({detail:"Invalid activity quantity or status."},422,headers);
        for(const [table,id,label] of [["bt_orders",b.related_order_id,"order"],["bt_services",b.related_service_id,"service"],["bt_products",b.product_id,"product"]])if(id!==undefined&&id!==null&&!await first(env.DB,"SELECT id FROM "+table+" WHERE id=?",[id]))return json({detail:"Selected "+label+" was not found."},400,headers);
        const id=await insert(env.DB,"bt_activities",{employee_id:employee,related_order_id:b.related_order_id||null,related_service_id:b.related_service_id||null,task_type:String(b.task_type||""),product_id:b.product_id||null,quantity,unit:String(b.unit||""),assigned_by:user.username,start_time:String(b.start_time||""),completion_time:String(b.completion_time||""),task_status:status,verified_by:"",proof_ref:String(b.proof_ref||""),remarks:String(b.remarks||""),created_at:new Date().toISOString()});
        return json({success:true,id},200,headers);
      }
      const activity=/^\/api\/business\/activities\/(\d+)$/.exec(path);
      if(activity&&request.method==="PATCH"){
        const b=await readJson(request),allowed=["task_status","start_time","completion_time","verified_by","proof_ref","remarks"],v={};
        for(const key of allowed)if(b[key]!==undefined)v[key]=b[key];
        if(!Object.keys(v).length)return json({detail:"No activity changes were supplied."},422,headers);
        if(v.task_status!==undefined&&!["Pending","In Progress","Completed","Blocked","Cancelled"].includes(v.task_status))return json({detail:"Invalid activity status."},422,headers);
        const old=await first(env.DB,"SELECT * FROM bt_activities WHERE id=?",[Number(activity[1])]);if(!old)return json({detail:"Activity not found."},404,headers);
        if(v.task_status==="In Progress"&&!v.start_time&&!old.start_time)v.start_time=new Date().toISOString();
        if(v.task_status==="Completed"&&!v.completion_time&&!old.completion_time)v.completion_time=new Date().toISOString();
        await update(env.DB,"bt_activities",v,Number(activity[1]));return json({success:true},200,headers);
      }
      if(path==="/api/business/stock-ledger"&&request.method==="GET"){
        const limit=Math.min(1000,Math.max(1,Number(url.searchParams.get("limit")||300))),product=url.searchParams.get("product_id");
        const sql="SELECT l.*,p.name AS product_name,p.sku FROM bt_stock_ledger l LEFT JOIN bt_products p ON p.id=l.product_id"+(product?" WHERE l.product_id=?":"")+" ORDER BY l.id DESC LIMIT ?";
        return json(await all(env.DB,sql,product?[Number(product),limit]:[limit]),200,headers);
      }
      if(path==="/api/business/stock-ledger"&&request.method==="POST"){
        const b=await readJson(request),movement=String(b.txn_type||"").trim().toLowerCase(),quantity=Number(b.quantity);
        const movements={receive:["received_qty",1,false],reserve:["reserved_qty",1,true],release:["reserved_qty",-1,false],dispatch:["dispatched_qty",1,true],free:["free_qty",1,true],return:["returned_qty",1,false],damage:["damaged_qty",1,true],expire:["expired_qty",1,true],quarantine:["quarantined_qty",1,true],unquarantine:["quarantined_qty",-1,false]};
        if(!movements[movement]||!Number.isFinite(quantity)||quantity<=0)return json({detail:"Unsupported movement or invalid quantity."},422,headers);
        const [field,direction,consumes]=movements[movement],product=await first(env.DB,"SELECT * FROM bt_products WHERE id=?",[Number(b.product_id)]);
        if(!product)return json({detail:"Product not found."},404,headers);
        const available=availableStock(product);
        if(consumes&&quantity>Math.max(0,available))return json({detail:"Movement exceeds available stock."},409,headers);
        if(direction<0&&quantity>Number(product[field]||0))return json({detail:"Movement exceeds the quantity currently held in that stock state."},409,headers);
        const now=new Date().toISOString();
        await env.DB.prepare("UPDATE bt_products SET "+field+"=COALESCE("+field+",0)+?,updated_by=?,updated_at=? WHERE id=?").bind(quantity*direction,user.username,now,Number(b.product_id)).run();
        const id=await insert(env.DB,"bt_stock_ledger",{product_id:Number(b.product_id),txn_type:movement,quantity,unit:String(b.unit||""),reference:String(b.reference||""),notes:String(b.notes||""),created_by:user.username,created_at:now});
        const updatedProduct=await first(env.DB,"SELECT * FROM bt_products WHERE id=?",[Number(b.product_id)]);
        return json({success:true,id,available_stock:availableStock(updatedProduct)},200,headers);
      }

      if(path==="/api/business/products"&&request.method==="GET"){
        const rows=await all(env.DB,"SELECT * FROM bt_products ORDER BY name COLLATE NOCASE");
        return json(rows.map(r=>({...r,available_stock:availableStock(r)})),200,headers);
      }
      if(path==="/api/business/products"&&request.method==="POST"){
        const b=await readJson(request);if(!String(b.name||"").trim())return json({detail:"Product name is required."},422,headers);
        const keys=["name","sku","category","brand","package_type","base_unit","opening_stock","received_qty","reserved_qty","dispatched_qty","free_qty","returned_qty","damaged_qty","expired_qty","quarantined_qty","purchase_cost","selling_price","reorder_level","batch_number","expiry_date","storage_location"];
        const v=Object.fromEntries(keys.map(k=>[k,b[k]??(k==="base_unit"?"PCS":k==="category"?"General":["name","sku","brand","package_type","batch_number","expiry_date","storage_location"].includes(k)?"":0)]));
        v.updated_by=user.username;v.updated_at=new Date().toISOString();
        try{return json({success:true,id:await insert(env.DB,"bt_products",v)},200,headers);}catch{return json({detail:"A product with that SKU already exists."},409,headers);}
      }
      if(path==="/api/business/services"&&request.method==="GET")return json(await all(env.DB,"SELECT * FROM bt_services ORDER BY name COLLATE NOCASE"),200,headers);
      if(path==="/api/business/services"&&request.method==="POST"){
        const b=await readJson(request);if(!String(b.name||"").trim())return json({detail:"Service name is required."},422,headers);
        const v={name:String(b.name).trim(),category:b.category||"Training",description:b.description||"",training_mode:b.training_mode||"Offline",service_unit:b.service_unit||"Session",session_duration:Number(b.session_duration||0),num_sessions:Number(b.num_sessions||0),plan_validity:Number(b.plan_validity||0),standard_price:Number(b.standard_price||0),active:b.active===undefined?1:Number(!!b.active),updated_at:new Date().toISOString()};
        return json({success:true,id:await insert(env.DB,"bt_services",v)},200,headers);
      }


      if(path==="/api/employee-groups"&&request.method==="GET"){
        const groups=await all(env.DB,"SELECT id,name,display_order FROM employee_groups ORDER BY display_order ASC,name COLLATE NOCASE");
        const counts=await all(env.DB,"SELECT TRIM(department) AS group_name,COUNT(*) AS employee_count FROM employees WHERE department IS NOT NULL AND TRIM(department)<>'' GROUP BY TRIM(department)");
        const byName=new Map();
        for(const g of groups){const k=String(g.name||"").trim().toLowerCase();if(k)byName.set(k,{id:g.id,name:g.name,display_order:Number(g.display_order||0),employee_count:0});}
        for(const r of counts){const k=String(r.group_name||"").trim().toLowerCase();if(!k)continue;if(byName.has(k))byName.get(k).employee_count=Number(r.employee_count||0);else byName.set(k,{id:null,name:r.group_name,display_order:9999,employee_count:Number(r.employee_count||0)});}
        return json([...byName.values()].sort((a,b)=>a.display_order-b.display_order||a.name.localeCompare(b.name)),200,headers);
      }
      if(path==="/api/business/orders"&&request.method==="GET")return json(await all(env.DB,"SELECT id,external_order_id AS order_code,order_date,sales_channel AS channel,customer_name,contact,payment_mode,order_status AS status,discount,order_value,invoice_number,shipment_id,assigned_employee_id,updated_by,updated_at,remarks FROM bt_orders ORDER BY id DESC LIMIT 300"),200,headers);
      if(path==="/api/business/members"&&request.method==="GET")return json(await all(env.DB,"SELECT m.id,m.name AS full_name,m.contact AS phone,m.service_id,s.name AS plan_name,m.training_mode,m.registration_date,m.start_date,m.expiry_date AS end_date,m.sessions_purchased,m.sessions_completed,m.assigned_trainer_id,m.status,m.payment_status,m.invoice_ref,m.remarks FROM bt_members m LEFT JOIN bt_services s ON s.id=m.service_id ORDER BY m.id DESC LIMIT 300"),200,headers);
      if(path==="/api/business/activities"&&request.method==="GET")return json(await all(env.DB,"SELECT a.*,e.name AS employee_name,o.external_order_id AS order_code,s.name AS service_name,p.name AS product_name FROM bt_activities a LEFT JOIN employees e ON e.id=a.employee_id LEFT JOIN bt_orders o ON o.id=a.related_order_id LEFT JOIN bt_services s ON s.id=a.related_service_id LEFT JOIN bt_products p ON p.id=a.product_id ORDER BY a.id DESC LIMIT 300"),200,headers);
      if(path==="/api/business/overview"&&request.method==="GET"){
        const queries=[
          ["products","SELECT COUNT(*) AS n FROM bt_products"],["low_stock","SELECT COUNT(*) AS n FROM bt_products WHERE (COALESCE(opening_stock,0)+COALESCE(received_qty,0)+COALESCE(returned_qty,0)-COALESCE(reserved_qty,0)-COALESCE(dispatched_qty,0)-COALESCE(free_qty,0)-COALESCE(damaged_qty,0)-COALESCE(expired_qty,0)-COALESCE(quarantined_qty,0))<=COALESCE(reorder_level,0)"],
          ["orders","SELECT COUNT(*) AS n FROM bt_orders"],["services","SELECT COUNT(*) AS n FROM bt_services"],["members","SELECT COUNT(*) AS n FROM bt_members"],["activities","SELECT COUNT(*) AS n FROM bt_activities"],
          ["open_orders","SELECT COUNT(*) AS n FROM bt_orders WHERE lower(IFNULL(order_status,'')) NOT IN ('completed','cancelled','delivered','closed','returned')"],["active_members","SELECT COUNT(*) AS n FROM bt_members WHERE lower(IFNULL(status,'')) IN ('active','current','ongoing') OR IFNULL(status,'')=''"],["completed_activities","SELECT COUNT(*) AS n FROM bt_activities WHERE lower(IFNULL(task_status,''))='completed'"]
        ];
        const values=await Promise.all(queries.map(([,sql])=>first(env.DB,sql)));
        return json(Object.fromEntries(queries.map(([k],i)=>[k,Number(values[i]?.n||0)])),200,headers);
      }
      if(path==="/api/print-center/summary"&&request.method==="GET"){
        const day=url.searchParams.get("report_date")||new Date().toISOString().slice(0,10);
        if(!validDate(day))return json({detail:"report_date must use YYYY-MM-DD format"},422,headers);
        const [tasks,attendance,employees,open,marked,orders,members]=await Promise.all([
          all(env.DB,"SELECT t.*,e.name AS employee_name FROM tasks t LEFT JOIN employees e ON e.id=t.employee_id WHERE t.task_date=? ORDER BY t.id DESC LIMIT 200",[day]),
          all(env.DB,"SELECT e.name,e.department,COALESCE(a.attendance_status,'Unmarked') AS attendance_status,a.check_in,a.check_out FROM employees e LEFT JOIN attendance a ON a.employee_id=e.id AND a.work_date=? WHERE e.active=1 ORDER BY e.name",[day]),
          first(env.DB,"SELECT COUNT(*) AS n FROM employees WHERE active=1"),
          first(env.DB,"SELECT COUNT(*) AS n FROM tasks WHERE lower(IFNULL(status,'')) NOT IN ('done','completed','closed')"),
          first(env.DB,"SELECT COUNT(*) AS n FROM attendance WHERE work_date=?",[day]),
          first(env.DB,"SELECT COUNT(*) AS n FROM bt_orders"),
          first(env.DB,"SELECT COUNT(*) AS n FROM bt_members")
        ]);
        return json({report_date:day,employee_count:Number(employees?.n||0),employees:Number(employees?.n||0),tasks_open:Number(open?.n||0),attendance_today:Number(marked?.n||0),orders:Number(orders?.n||0),members:Number(members?.n||0),tasks,attendance,note:"Live web summary from the shared D1 database."},200,headers);
      }
      if(path==="/api/customers/prospects"&&request.method==="GET"){
        const where=["1=1"],args=[];
        if(url.searchParams.has("state")){where.push("state=?");args.push(url.searchParams.get("state"));}
        if(url.searchParams.has("q")){const term="%"+url.searchParams.get("q").trim()+"%";const fields=["business_name","business_category","kind","area","city","state","contact_person","phone","email","address","website","maps","followup_date","connection","verified","response","source_status"];where.push("("+fields.map(f=>"IFNULL("+f+",'') LIKE ?").join(" OR ")+")");args.push(...fields.map(()=>term));}
        if(url.searchParams.has("before_id")){const id=Number(url.searchParams.get("before_id"));if(Number.isInteger(id)&&id>0){where.push("id<?");args.push(id);}}
        const limit=Math.min(1000,Math.max(1,Number(url.searchParams.get("limit")||200)));
        args.push(limit);
        return json(await all(env.DB,"SELECT * FROM customer_prospects WHERE "+where.join(" AND ")+" ORDER BY id DESC LIMIT ?",args),200,headers);
      }
      if(path==="/api/customers/summary"&&request.method==="GET"){
        const [total,states,cities]=await Promise.all([first(env.DB,"SELECT COUNT(*) AS n FROM customer_prospects"),all(env.DB,"SELECT state,COUNT(*) AS count FROM customer_prospects GROUP BY state ORDER BY count DESC LIMIT 30"),all(env.DB,"SELECT city,state,COUNT(*) AS count FROM customer_prospects GROUP BY city,state ORDER BY count DESC LIMIT 30")]);
        return json({total:Number(total?.n||0),states,cities},200,headers);
      }
      if(path==="/api/customers/regional-summary"&&request.method==="GET"){
        const rows=await all(env.DB,"SELECT state,city,COUNT(*) AS stores FROM customer_prospects GROUP BY state,city ORDER BY state COLLATE NOCASE,stores DESC");
        const states=await all(env.DB,"SELECT state,COUNT(*) AS stores FROM customer_prospects GROUP BY state ORDER BY stores DESC");
        return json({total:rows.reduce((n,r)=>n+Number(r.stores||0),0),states,territories:rows},200,headers);
      }

      return json({ error: "Not found", path }, 404, headers);
    } catch (error) {
      console.error("Cloudflare API request failed", { path: url.pathname, message: String(error?.message || error) });
      const detail = String(error?.message || error);
      if (/UNIQUE constraint failed/i.test(detail)) return json({detail:"A record with the same unique value already exists."},409,headers);
      return json({ error: "Internal API error" }, 500, headers);
    }
  },
};

async function all(db,sql,args=[]){const r=await db.prepare(sql).bind(...args).all();return r.results||[];}
async function first(db,sql,args=[]){return db.prepare(sql).bind(...args).first();}
async function insert(db,table,values){const keys=Object.keys(values),sql="INSERT INTO "+table+"("+keys.join(",")+") VALUES("+keys.map(()=>"?").join(",")+")";const r=await db.prepare(sql).bind(...keys.map(k=>values[k])).run();return Number(r.meta?.last_row_id||0);}
async function update(db,table,values,id){const keys=Object.keys(values);if(!keys.length)return;await db.prepare("UPDATE "+table+" SET "+keys.map(k=>k+"=?").join(",")+" WHERE id=?").bind(...keys.map(k=>values[k]),id).run();}
async function ensureGroup(db,name,now){const n=String(name||"").trim();if(!n)return;const old=await first(db,"SELECT id FROM employee_groups WHERE name=? COLLATE NOCASE",[n]);if(old)return;const row=await first(db,"SELECT COALESCE(MAX(display_order),0)+10 AS n FROM employee_groups");await db.prepare("INSERT INTO employee_groups(name,display_order,created_at) VALUES(?,?,?)").bind(n,Number(row?.n||10),now).run();}
async function upsertTarget(db,employee,date,target,status,now){await db.prepare("INSERT INTO employee_targets(employee_id,target_date,target,target_status,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(employee_id,target_date) DO UPDATE SET target=excluded.target,target_status=excluded.target_status,updated_at=excluded.updated_at").bind(employee,date,String(target||""),String(status||""),now).run();}
async function audit(db,user,action,details){await db.prepare("INSERT INTO audit_log(timestamp,action,details) VALUES(?,?,?)").bind(new Date().toISOString(),action,user.username+": "+details).run();}
function taskValues(b){const status=String(b.status??"Not started").trim(),custom=b.custom_values??b.custom_fields??"";return {employee_id:Number(b.employee_id||1),task_date:String(b.task_date||new Date().toISOString().slice(0,10)),title:String(b.title||"").trim(),department:String(b.department||b.category||"").trim(),details:String(b.details||b.notes||"").trim(),due_time:String(b.due_time||"").trim(),priority:String(b.priority||"Normal").trim(),status,progress:Number(b.progress||0),proof_url:String(b.proof_url||"").trim(),proof_note:String(b.proof_note||"").trim(),submitted_at:String(b.submitted_at||""),manager_note:String(b.manager_note||b.next_action||"").trim(),expose_link:b.expose_link?1:0,target_qty:String(b.target_qty||"").trim(),actual_qty:String(b.actual_qty||"").trim(),next_action:String(b.next_action||b.manager_note||"").trim(),custom_values:typeof custom==="string"?custom:JSON.stringify(custom)};}
function normalizeWeekdays(value){const a=String(value||"0,1,2,3,4,6").split(",").map(Number).filter(n=>Number.isInteger(n)&&n>=0&&n<=6);return [...new Set(a.concat([6]))].sort();}
function validDate(s){if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;const d=new Date(s+"T00:00:00Z");return !Number.isNaN(d.getTime())&&d.toISOString().slice(0,10)===s;}
function addDays(value,n=1){const d=new Date(value+"T00:00:00Z");d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);}
function validTime(s){return /^([01]\d|2[0-3]):[0-5]\d$/.test(s);}
function availableStock(p){return Math.max(0,Number(p.opening_stock||0)+Number(p.received_qty||0)+Number(p.returned_qty||0)-Number(p.reserved_qty||0)-Number(p.dispatched_qty||0)-Number(p.free_qty||0)-Number(p.damaged_qty||0)-Number(p.expired_qty||0)-Number(p.quarantined_qty||0));}
function publicUser(u){return {id:u.id,username:u.username,display_name:u.display_name||u.username,role:u.role};}
function role(user){return String(user?.role||"").trim().toLowerCase();}
function forbidden(headers){return json({detail:"You do not have permission to perform this action."},403,headers);}
async function currentUser(request, env) {
  const token = bearer(request);
  if (!token || token.length > 256) return null;
  const hash = await sha256(token);
  const row = await env.DB.prepare(
    "SELECT u.id, u.username, u.display_name, u.role FROM web_auth_sessions s JOIN auth_users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1"
  ).bind(hash, new Date().toISOString()).first();
  return row ? publicUser(row) : null;
}
function bearer(request) {const value=request.headers.get("Authorization")||"";const match=/^Bearer\s+(.+)$/i.exec(value);return match?match[1].trim():"";}

async function deriveHash(password,salt){const key=await crypto.subtle.importKey("raw",encoder.encode(String(password||"")),"PBKDF2",false,["deriveBits"]);const bits=await crypto.subtle.deriveBits({name:"PBKDF2",salt:encoder.encode(salt),iterations:PBKDF2_ITERATIONS,hash:"SHA-256"},key,256);return [...new Uint8Array(bits)].map(v=>v.toString(16).padStart(2,"0")).join("");}
function normalizeAnswer(value){return String(value||"").trim().toLocaleLowerCase().split(/\s+/).filter(Boolean).join(" ");}
function strongPassword(value){const s=String(value||"");return s.length>=8&&/[A-Za-z]/.test(s)&&/[0-9]/.test(s);}

async function verifyPassword(password,salt,expected){if(typeof salt!=="string"||typeof expected!=="string"||!/^[a-f0-9]{64}$/i.test(expected))return false;const key=await crypto.subtle.importKey("raw",encoder.encode(password),"PBKDF2",false,["deriveBits"]);const bits=await crypto.subtle.deriveBits({name:"PBKDF2",salt:encoder.encode(salt),iterations:PBKDF2_ITERATIONS,hash:"SHA-256"},key,256);const actual=[...new Uint8Array(bits)].map(v=>v.toString(16).padStart(2,"0")).join("");return constantTimeEqual(actual,expected.toLowerCase());}
function constantTimeEqual(a,b){if(a.length!==b.length)return false;let d=0;for(let i=0;i<a.length;i++)d|=a.charCodeAt(i)^b.charCodeAt(i);return d===0;}
async function sha256(value){const digest=await crypto.subtle.digest("SHA-256",encoder.encode(value));return [...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,"0")).join("");}
function randomHex(bytes){const data=crypto.getRandomValues(new Uint8Array(bytes));return [...data].map(v=>v.toString(16).padStart(2,"0")).join("");}
async function readJson(request){const length=Number(request.headers.get("Content-Length")||0);if(length>1048576)throw new Error("Request too large");return request.json();}
function json(body,status,headers){return new Response(JSON.stringify(body),{status,headers});}
