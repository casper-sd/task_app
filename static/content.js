function getCookie(key){
    let cks = document.cookie.split('; ')
    for(let i =0; i < cks.length; i++){
        if(cks[i].startsWith(key + '=')){
            return cks[i].split('=')[1]
        }
    }
    return null;
}

var HomeVue = new Vue({
    el: '#home',
    data: {
        formtype: '',
        formid: null,
        show_popup: false,
        heading: "",
        fields: [],
        values: {},
        null_count: 0,

        submitted: false,
        show_alert: false,
        alert_msg: '',
        alert_style: 'alert alert-success',
        aci: 0,
        cards: [],
        selected_list: null,
        ali: 0,
        lists: [],
        card_moving: false,
        mfli: 0,
        moving_card_text: 'Move'
    },
    mounted: async function(){
        let resp = await fetch("/data?rtype=lists", {
            headers: { 'TZ': new Date().getTimezoneOffset() },
        })
        this.lists = await resp.json()
        this.ali = 0
    },
    methods: {
        async new_list() {
            this.formtype = 'newlist'
            this.reqFormData()
        },
        async select_list(arg){
            if(this.selected_list === null){
                this.selected_list = this.lists[arg]
                let resp = await fetch(`/data?rtype=cards&id=${this.selected_list.id}`, {
                    headers: { 'TZ': new Date().getTimezoneOffset() },
                })
                this.cards = await resp.json()
            }else{
                this.card_moving = false
                this.selected_list = null
                this.cards = []
            }
        },
        async new_card(){
            this.formtype = 'newcard'
            this.formid = this.selected_list.id
            this.reqFormData()
        },
        async editcard(arg){
            this.formtype = 'editcard'
            this.formid = this.cards[arg].id
            this.reqFormData()
        },
        async card_op(arg, rtype){
            this.submitted = true
            if(rtype === 'move'){this.cards[arg].list_id = this.lists[this.ali].id}
            else if(rtype === 'complete'){this.formtype = 'completecard'}
            else if(rtype === 'delete'){this.formtype = 'deletecard'}
            let resp = await fetch(`/card?rtype=${rtype}`, {
                method: 'POST',
                mode: 'cors',
                cache: 'no-cache',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'TZ': new Date().getTimezoneOffset() },
                redirect: 'follow',
                referrerPolicy: 'no-referrer',
                body: JSON.stringify(this.cards[arg])
            })
            let stat = await resp.json()
            let status = stat.status;
            let status_msg = stat.msg;
            if(status){
                this.alert_style = 'alert alert-success'
            }else{
                this.alert_style = 'alert alert-danger'
            }
            this.alert_msg = status_msg
            this.show_alert = true
            setTimeout(async () => {
                await this.refresh()
                this.show_alert = false
                this.alert_msg = ''
                this.submitted = false
            }, 2000)
        },
        movecard(arg){
            if(this.card_moving){
                this.moving_card_text = 'Move'
                this.card_moving = false
                if(this.mfli != this.ali){
                    this.formtype = 'movecard'
                    this.card_op(arg, 'move')
                }
            }else{
                this.mfli = this.ali
                this.moving_card_text = 'Cancel Move'
                this.card_moving = true
            }
        },
        scroll_list(a){
            let ll = this.lists.length + 1
            if(!this.card_moving){this.selected_list = null; this.aci = 0}
            else{ ll = this.lists.length;}
            
            if(a === 'prev'){this.ali = ((this.ali - 1)%ll + ll)%ll}
            else if(a === 'next'){this.ali = (this.ali + 1)%ll}

            if(this.card_moving){
                if(this.mfli == this.ali) {this.moving_card_text = 'Cancel Move'}
                else {this.moving_card_text = 'Confirm'}
            }
        },
        scroll_card(a){
            let cc = this.cards.length + 1
            if(a === 'prev'){this.aci = ((this.aci - 1)%cc + cc)%cc}
            else if(a === 'next'){this.aci = (this.aci + 1)%cc}
        },
        ///////////////////////////////////////////////////////////////////////////////

        async reqFormData(){
            let url = `/formdata?type=${this.formtype}&id=${this.formid}`
            let response = await fetch(url, {
                headers: { 'TZ': new Date().getTimezoneOffset() },
            })
            let data = await response.json()
            this.heading = data.heading
            this.fields = data.fields
            this.values = data.values
            this.submitted = false
            this.show_popup = true
        },
        async sendFormData(){
            this.submitted = true
            this.null_count = 0
            let nc = 0
            
            for(let f in this.fields){
                let field = this.fields[f]
                if(this.values[field.name] === "") nc += 1
            }
            this.null_count = nc
            if(this.null_count >  0){
                setTimeout(() => {
                    this.submitted = false
                }, 5000);
                return
            }

            // --------------------------------------------------------------------

            const response = await fetch(`/formdata?type=${this.formtype}&id=${this.formid}`, {
                method: 'POST',
                mode: 'cors',
                cache: 'no-cache',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'TZ': new Date().getTimezoneOffset() },
                redirect: 'follow',
                referrerPolicy: 'no-referrer',
                body: JSON.stringify(this.values)
            });
            let resp =  await response.json()

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
            setTimeout(async () => {
                this.show_alert = false
                this.alert_msg = ''
                if(!status){this.submitted = false}
                else{
                    await this.refresh()
                    this.show_popup = false
                    this.values = {}
                }
            }, 3000)
        },
        hidepopup(){
            this.show_popup = false
            this.values = {}
        },
        async refresh(d){
            if(this.formtype === 'newlist'){
                let resp = await fetch("/data?rtype=lists", {
                    headers: { 'TZ': new Date().getTimezoneOffset() },
                })
                this.lists = await resp.json()
                return
            }

            if(this.formtype === 'newcard' || this.formtype === 'editcard' || this.formtype === 'completecard' || this.formtype === 'deletecard'){
                let resp = await fetch("/data?rtype=lists", {
                    headers: { 'TZ': new Date().getTimezoneOffset() },
                })
                this.lists = await resp.json()
                resp = await fetch(`/data?rtype=cards&id=${this.lists[this.ali].id}`, {
                    headers: { 'TZ': new Date().getTimezoneOffset() },
                })
                this.cards = await resp.json()
                return
            }

            if(this.formtype === 'movecard'){
                let resp = await fetch("/data?rtype=lists", {
                    headers: { 'TZ': new Date().getTimezoneOffset() },
                })
                this.lists = await resp.json()
                this.ali = this.mfli
                resp = await fetch(`/data?rtype=cards&id=${this.lists[this.ali].id}`, {
                    headers: { 'TZ': new Date().getTimezoneOffset() },
                })
                this.cards = await resp.json()
                return
            }
        }
    }
});


new Vue({
    el: '#navigation',
    mounted: function(){
        this.user_fname = getCookie('f_name')
        this.user_lname = getCookie('l_name')
    },
    data: {
        user_fname: '',
        user_lname: '',
        taskid: null,
        cst: null
    },
    methods: {
        async logout(){
            await fetch('/logout')
            location.reload()
        },
        async download(){
            if(this.taskid !== null){
                alert('Already requested. Wait for the download to start')
                return
            }
            let res = await (await fetch('/download', {
                headers: { 'TZ': new Date().getTimezoneOffset() },
            })).json()
            this.taskid = res.id
            if(res.status){
                alert(res.msg)
            }
            this.cst = setInterval(this.check_status, 1000)
        },
        async check_status(){
            let r = await fetch('/download_status', {
                method: 'POST',
                body: JSON.stringify({id: this.taskid})
            })
            if(r.ok){
                let b = await r.blob()
                window.location.assign(window.URL.createObjectURL(b))
                clearInterval(this.cst)
                this.taskid = null
            }
        }
    }
})