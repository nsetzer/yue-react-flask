import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Button from 'material-ui/Button';

import Tabs, { Tab } from 'material-ui/Tabs';

import AppBar from 'material-ui/AppBar';

import Settings from 'material-ui-icons/Settings';
import LibraryMusic from 'material-ui-icons/LibraryMusic';
import * as ListIcons from 'material-ui-icons/List';
const ListIcon = ListIcons.default

import SoundView from "./player/SoundView"
import QueueView from "./QueueView"
import DomainView from "./DomainView"
import DomainArtistView from "./DomainArtistView"
import DomainAlbumView from "./DomainAlbumView"

import Grid from 'material-ui/Grid';

import { Route, Switch } from 'react-router-dom';

import History from '../history'

interface Dictionary<T> {
    [Key: string]: T;
}

import Drawer from 'material-ui/Drawer';

const drawerWidth = 240;

const navStyles : Dictionary<React.CSSProperties> = {
  drawerPaper: {
    position: 'relative',
    height: '100%',
    width: drawerWidth,
  },
}

export interface AppSideNavProps {
  permanent: boolean,
  open: boolean,
  onRequestClose: (event) => void
};

export interface AppSideNavState {
}
class AppSideNav extends React.Component<AppSideNavProps,AppSideNavState> {
  constructor(props) {
    super(props);
  }
  render() {
    return (
      <Drawer
      open={this.props.open}
      onRequestClose={this.props.onRequestClose}
      type={this.props.permanent?"permanent":"temporary"}

      anchor={"left"}>

      <div style={{width:drawerWidth}}>
      hello world
      </div>
      </Drawer>
    );
  }
}


export interface MainViewProps {
  logoutAndRedirect: PropTypes.func,
  userName: PropTypes.string,
};

export interface MainViewState {
  open: boolean,
  currentTabIndex: number,
  screenWidth: number,
  screenHeight: number
}

const style : Dictionary<React.CSSProperties> = {
  header: {
    textAlign: "center",
  },
  header_content: {
    padding: "5px",
    color: "white"
  }

}

class MainView extends React.Component<MainViewProps,MainViewState> {

  constructor(props) {
    super(props);
    this.state = {open:true,
                  currentTabIndex: 0,
                  screenWidth: 0,
                  screenHeight: 0};
    this.logout = this.logout.bind(this)
    this.onTabIndexChange = this.onTabIndexChange.bind(this)
    this.onResize = this.onResize.bind(this)

  }

  logout(e) {
      e.preventDefault();
      this.props.logoutAndRedirect();
      this.setState({
          open: false,
      });
  }

  onTabIndexChange(event, value) {
    this.setState({ currentTabIndex: value });
    if (value==0) {
      History.push("/main/queue");
    } else if (value==1) {
      History.push("/main/library");
    } else if (value==2) {
      History.push("/main/settings");
    }
  }

  componentDidMount() {
    this.onResize()
    window.addEventListener('resize', this.onResize)
  }

  componentWillUnmount() {
    window.removeEventListener('resize', this.onResize)
  }

  onResize() {
    this.setState({screenWidth:window.innerWidth,
                   screenHeight: window.innerHeight})
  }

  render() {

    return (
      <div>

      <div style={{marginLeft: drawerWidth}}>
      <AppBar style={{ position: "fixed", height:"160px" }} >
        <div style={style.header}>
          <header style={style.header_content}>

            <SoundView/>
          </header>
          <br/>
        </div>
      </AppBar>
      </div>
      {/*<AppSideNav open={false}
                  permanent={true}
                  onRequestClose={(e) => {}}
                  />*/}

      <main style={{ paddingTop: 160, marginLeft: drawerWidth }}>

      <h2>{this.state.screenWidth} x {this.state.screenHeight}</h2>
       <Button
            style={{ marginTop: 50 }}
            onClick={(e) => this.logout(e)}
            raised={true}
          >Logout</Button>

        <Tabs
            value={this.state.currentTabIndex}
            onChange={this.onTabIndexChange}
            fullWidth
            indicatorColor="accent"
            textColor="accent"
          >
          <Tab icon={<ListIcon />} label="Queue" />
          <Tab icon={<LibraryMusic />} label="Library" />
          <Tab icon={<Settings />} label="Settings" />
        </Tabs>

        <Switch>
        <Route path={`/main/queue`} component={QueueView}/>
        <Route exact path={`/main/library`} component={DomainView}/>
        <Route exact path={`/main/library/:artist`} component={DomainArtistView}/>
        <Route exact path={`/main/library/:artist/:album`} component={DomainAlbumView}/>
        <Route path={"/main"} render={() => (
          <div>
          <h3>View Not Implemented</h3>
          <Button
            onClick={(e) => History.goBack()}
          >Go Back</Button>
          </div>
        )}/>
        </Switch>
      </main>

      </div>
    );
  }
}

function mapStateToProps(state) {
  return {
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators({}, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(MainView);
