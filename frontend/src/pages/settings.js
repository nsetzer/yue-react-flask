from module daedalus import{
    StyleSheet,
    DomElement,
    ButtonElement,
    TextElement,
    TextInputElement,
    Router
}
import module api
import module components

const style = {
    main: StyleSheet({
        width: '100%',
    }),

    settingsItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'column',
        'padding-left': '1.1em',
        'padding-bottom': '.5em',
        //width: '100%',
        border-bottom: {style: "solid", width: "1px"}
    }),

    settingsRowItem: StyleSheet({
        display: 'flex',
        'flex-direction': 'row',
        'padding-left': '1.1em',
        'padding-bottom': '.5em',
        border-bottom: {style: "solid", width: "1px"}
    }),
}

class SettingsItem extends DomElement {
    constructor(title) {
        super("div", {className: style.settingsItem}, []);


        this.appendChild(new TextElement(title))
    }
}

class SettingsButtonItem extends DomElement {
    constructor(title, action) {
        super("div", {className: style.settingsRowItem}, []);
        this.attrs.count = 0

        this.appendChild(new ButtonElement(title, () => {action(this)}))
    }

    setText(text) {
        //this.children[0].setText(text)
    }
}

class SettingsGroupItem extends DomElement {
    constructor(title, names) {
        super("div", {className: style.settingsItem}, []);

        this.appendChild(new TextElement(title))

        this.appendChild(new DomElement("br", {}, []))

        const form = this.appendChild(new DomElement("form", {}, []))
        names.forEach(name => {

            const child = form.appendChild(new DomElement("div", {}, []))
            const btn = child.appendChild(new DomElement("input", {type:"radio", value: name, name: this.props.id}));
            child.appendChild(new DomElement("label", {'forx': btn.props.id}, [new TextElement(name)]))
            //child.appendChild(new DomElement("br", {}, []))
        }
    }
}

class Header extends components.NavHeader {
    constructor(parent) {
        super();
        this.addAction(resources.svg['menu'], ()=>{});
    }
}

export class SettingsPage extends DomElement {
    constructor() {
        super("div", {className: style.main}, []);

        this.attrs = {
            header: new Header(this),
            container: new DomElement("div", {}, [])
        }

        this.appendChild(this.attrs.header)
        this.appendChild(this.attrs.container)


        this.attrs.container.appendChild(new SettingsItem("Volume:"))
        this.attrs.container.appendChild(new SettingsGroupItem("Audio Backend:", ["Cloud", "Cloud Native", "Native"]))
        this.attrs.container.appendChild(new SettingsButtonItem("file api test",
            (item) => {
                if (Client) {
                    console.log("test")
                    item.attrs.count += 1
                    if (Client.fileExists("sample.dat")) {
                        item.setText(item.attrs.count + " : " + "T")
                    } else {
                        item.setText(item.attrs.count + " : " + "F")
                        const url = "http://192.168.1.149:4100/static/index.js";
                        const folder = 'Music/test';
                        const name = 'index.js';

                        Client.downloadUrl(url, folder, name)
                    }
                }
            }));

        this.attrs.container.appendChild(new SettingsButtonItem("load",
            (item) => {
                if (daedalus.platform.isAndroid) {

                    const url1 = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
                    const url2 = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
                    const url3 = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"
                    const queue = [ {url: url1}, {url: url2}, {url: url3}];

                    const data = JSON.stringify(queue)
                    console.log(data)
                    AndroidNativeAudio.setQueue(data);


                    AndroidNativeAudio.loadIndex(0);
                }
            }));

        this.attrs.container.appendChild(new SettingsButtonItem("play",
            (item) => {
                if (daedalus.platform.isAndroid) {
                    AndroidNativeAudio.play();
                }
            }));

        this.attrs.container.appendChild(new SettingsButtonItem("pause",
            (item) => {
                if (daedalus.platform.isAndroid) {
                    AndroidNativeAudio.pause();
                }
            }));

        this.attrs.container.appendChild(new SettingsButtonItem("next",
            (item) => {
                if (daedalus.platform.isAndroid) {
                    AndroidNativeAudio.skipToNext();
                }
            }));

        this.attrs.container.appendChild(new SettingsButtonItem("prev",
            (item) => {
                if (daedalus.platform.isAndroid) {
                    AndroidNativeAudio.skipToPrev();
                }
            }));

    }

}