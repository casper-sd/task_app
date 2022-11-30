new Vue({
    el: '#summary_bar',
    data: {
        labels: [],
        values: {},
        yticks: [],
        yscale: 1,
        ytickh: 0,
        lh: [],
        rh: [],
        lists: [],
        submitted: false,
        show_alert: false,
        stat_msg: '',
        ifscope: true
    },
    mounted: async function(){
        let resp = await fetch("/data?rtype=lists", {
            headers: { 'TZ': new Date().getTimezoneOffset() },
        })
        this.lists = await resp.json()
        this.fetch_data('past', 'all', '7', '1', 'day', 'day')
    },
    computed:{
        hspace: function(){
            let tw = this.$refs.chart.clientWidth
            let yax = this.$refs.yaxis.clientWidth
            let ll = this.labels.length
            let pp = (tw - yax - (ll * 80)) / (2*ll)
            if(pp < 0){pp = 2}
            return {
                'padding-left': `${pp}px`,
                'padding-right': `${pp}px`
            }
        },
        vspace: function(){
            return {'height': `${this.ytickh}px`}
        }
    },
    methods: {
        fetch_data: async function(s, id, ts, rs, tu, ru){
            this.submitted = true
            let res = await fetch(`/summary/data?scope=${s}`, {
                method: 'POST',
                mode: 'cors',
                cache: 'no-cache',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'TZ': new Date().getTimezoneOffset() },
                redirect: 'follow',
                referrerPolicy: 'no-referrer',
                body: JSON.stringify({
                    'id': id,
                    'tscale': ts,
                    'tunit': tu,
                    'rscale': rs,
                    'runit': ru
                })
            })
            if(!res.ok){
                this.stat_msg = await res.text()
                this.show_alert = true
                setTimeout(()=>{
                    this.stat_msg = ''
                    this.show_alert = false
                    this.submitted = false
                }, 5000)
                return
            }
            let data = await res.json()
            this.labels = data['time_series']
            this.values = data['frequency']
            console.log(this.values)
            this.lh = []
            this.rh = []
            this.ifscope = (s == 'past')
            let other = this.ifscope? 'created':'due'
            for(let i=0; i<this.labels.length; i++){
                if(i !== 0){this.lh.push(this.values['completed'][i-1])}
                else{this.lh.push(0)}
                if(i+1 !== this.labels.length){this.rh.push(this.values[other][i])}
                else{this.rh.push(0)}
            }

            let chart_height = this.$refs.yaxis.clientHeight
            let ylim = Math.max(Math.max(...this.values[other]), Math.max(...this.values['completed'])) + 1

            this.yscale = chart_height / ylim
            this.ytickh = chart_height / 10
            let dy = ylim / 10
            this.yticks = []
            for(let i = dy; i < ylim; i+=dy){
                this.yticks.unshift((i - dy*0.5).toFixed(2))
            }
            this.submitted = false
            
        },
        lst: function(arg){
            return {'height': `${this.lh[arg]*this.yscale}px`}
        },
        rst: function(arg){
            return {'height': `${this.rh[arg]*this.yscale}px`}
        },
        reqdata: async function(){
            let id = this.$refs.taskid.value
            let runit = this.$refs.runit.value
            let rscale = this.$refs.rscale.value
            let tunit = this.$refs.tunit.value
            let tscale = this.$refs.tscale.value
            let scope = this.$refs.scope.value
            await this.fetch_data(scope, id, tscale, rscale, tunit, runit)
        }
    }
})