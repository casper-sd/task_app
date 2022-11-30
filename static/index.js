new Vue({
    el: "#login_app",
    data: {
        stage: 0,
        submitted: false,
        null_count: 0,
        show_alert: false,
        alert_msg: '',
        alert_style: 'alert alert-success',
        current: [{
            req: 'login',
            enb: 'Login',
            go_btn: "Log in",
            heading: "Welcome back! Login to Kanban Application",
            fields: [
                {name: "uid", text:"User ID", ph: "Your ID", type: "text", required: true, disabled: false},
                {name: "pwd", text:"Your Password", ph: "Your Password", type: "password", required: true, disabled: false},
            ],
            values: {
                req: 'login',
                uid: '', pwd: ''
            }
        }],
        other1: [{
            req: 'reg_acc',
            enb: 'Sign Up',
            heading: "Welcome! Register to Kanban Application",
            go_btn: "Register",
            fields: [
                {name: "fname", text:"First Name", ph: "Enter your First Name", type: "text", required: true, disabled: false},
                {name: "lname", text:"Last Name", ph: "Enter your Last Name", type: "text", required: true, disabled: false},
                {name: "email", text:"Your Email ID", ph: "Enter your Email", type: "email", required: true, disabled: false},
                {name: "uid", text:"Preferred User ID", ph: "Your ID Here", type: "text", required: true, disabled: false},
                {name: "pwd", text:"Your Password", ph: "Your Password", type: "password", required: true, disabled: false},
            ],
            values: {
                req: 'reg_acc',
                fname: '', lname: '', email: '', uid: '', pwd: ''
            }
        },
        {
            req: 'valid_acc',
            go_btn: "Verify",
            fields: [
                {name: "vcode", text:"Enter the Verification Code Sent to Email", ph: "Enter 6-digit Code Here", type: "number", required: true, disabled: false}
            ],
            values: {
                req: 'valid_acc',
                vcode: ''
            }
        }],
        other2: [
            {
                req: 'recov_acc',
                enb: 'Recover Account',
                heading: "Recover Your Account",
                go_btn: "Send Code",
                fields: [
                    {name: "email", text:"Your Email ID", ph: "Enter your Email", type: "email", required: true, disabled: false}
                ],
                values: {
                    req: 'recov_acc',
                    email: ''
                }
            },
            {
                req: 'valid_acc',
                go_btn: "Verify",
                fields: [
                    {name: "vcode", text:"Enter the Verification Code Sent to Email", ph: "Enter 6-digit Code Here", type: "number", required: true, disabled: false}
                ],
                values: {
                    req: 'valid_acc',
                    vcode: ''
                }
            },
            {
                req: 'new_pass',
                go_btn: "Set Password",
                fields: [
                    {name: "newpass", text:"New Password", ph: "Enter your new password", type: "password", required: true, disabled: false}
                ],
                values: {
                    req: 'new_pass',
                    newpass: ''
                }
            }
        ]
    },
    methods: {
        changeTo(arg){
            this.stage = 0
            if(arg === this.other1[0].req){
                let temp = this.other1
                this.other1 = this.current
                this.current = temp
            }
            else if(arg === this.other2[0].req){
                let temp = this.other2
                this.other2 = this.current
                this.current = temp
            }
        },
        async sendData(){
            this.submitted = true
            this.null_count = 0
            let nc = 0
            for(f in this.current[this.stage].fields){
                let field = this.current[this.stage].fields[f]
                if(this.current[this.stage].values[field.name] === "" && field.required) nc += 1
            }
            this.null_count = nc
            if(this.null_count >  0){
                setTimeout(() => {
                    this.submitted = false
                }, 5000);
                return
            }

            // --------------------------------------------------------------------

            const response = await fetch("/user", {
                method: 'POST',
                mode: 'cors',
                cache: 'no-cache',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                redirect: 'follow',
                referrerPolicy: 'no-referrer',
                body: JSON.stringify(this.current[this.stage].values)
            });
            let resp =  await response.json()
            console.log(resp)

            // --------------------------------------------------------------------

            let status = resp.status;
            let status_msg = resp.msg;
            if(status){
                this.alert_style = 'alert alert-success'
            }else{
                this.alert_style = 'alert alert-danger'
            }
            this.alert_msg = status_msg
            this.show_alert = true
            setTimeout(() => {
                this.show_alert = false
                this.alert_msg = ''
                if(this.current.length > this.stage + 1 && status){
                    this.stage += 1
                    this.submitted = false
                }else if(!status){this.submitted = false}
                else{
                    window.location = '/'
                }
            }, 3000)
        }
    }
})