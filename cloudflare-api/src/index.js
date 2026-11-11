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
        return json({ user }, 200, headers);
      }
      if (url.pathname === "/api/auth/logout" && request.method === "POST") {
        const token = bearer(request);
        if (!token) return json({ error: "Login required" }, 401, headers);
        const result = await env.DB.prepare("DELETE FROM web_auth_sessions WHERE token_hash = ?").bind(await sha256(token)).run();
        if (!result.success || !result.meta?.changes) return json({ error: "Login required" }, 401, headers);
        return json({ success: true }, 200, headers);
      }

      const user = await currentUser(request, env);
      if (!user) return json({ error: "Login required" }, 401, headers);
      const path = url.pathname;


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
        if((b.role==="Developer"||b.role==="Admin")&&!ADMIN_ROLES.has(role(user)))return forbidden(headers);
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
function availableStock(p){return Math.max(0,Number(p.opening_stock||0)+Number(p.received_qty||0)+Number(p.returned_qty||0)-Number(p.reserved_qty||0)-Number(p.dispatched_qty||0)-Number(p.damaged_qty||0)-Number(p.expired_qty||0)-Number(p.quarantined_qty||0));}
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
function normalizeAnswer(value){return String(value||"").trim().toLocaleLowerCase().split(/\\s+/).filter(Boolean).join(" ");}
function strongPassword(value){const s=String(value||"");return s.length>=8&&/[A-Za-z]/.test(s)&&/[0-9]/.test(s);}

async function verifyPassword(password,salt,expected){if(typeof salt!=="string"||typeof expected!=="string"||!/^[a-f0-9]{64}$/i.test(expected))return false;const key=await crypto.subtle.importKey("raw",encoder.encode(password),"PBKDF2",false,["deriveBits"]);const bits=await crypto.subtle.deriveBits({name:"PBKDF2",salt:encoder.encode(salt),iterations:PBKDF2_ITERATIONS,hash:"SHA-256"},key,256);const actual=[...new Uint8Array(bits)].map(v=>v.toString(16).padStart(2,"0")).join("");return constantTimeEqual(actual,expected.toLowerCase());}
function constantTimeEqual(a,b){if(a.length!==b.length)return false;let d=0;for(let i=0;i<a.length;i++)d|=a.charCodeAt(i)^b.charCodeAt(i);return d===0;}
async function sha256(value){const digest=await crypto.subtle.digest("SHA-256",encoder.encode(value));return [...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,"0")).join("");}
function randomHex(bytes){const data=crypto.getRandomValues(new Uint8Array(bytes));return [...data].map(v=>v.toString(16).padStart(2,"0")).join("");}
async function readJson(request){const length=Number(request.headers.get("Content-Length")||0);if(length>1048576)throw new Error("Request too large");return request.json();}
function json(body,status,headers){return new Response(JSON.stringify(body),{status,headers});}
