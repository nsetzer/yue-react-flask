import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Button from 'material-ui/Button';

import Tabs, { Tab } from 'material-ui/Tabs';

import AppBar from 'material-ui/AppBar';

import Settings from 'material-ui-icons/Settings';
import ExitToApp from 'material-ui-icons/ExitToApp';
import LibraryMusic from 'material-ui-icons/LibraryMusic';
import * as ListIcons from 'material-ui-icons/List';
const ListIcon = ListIcons.default


import Divider from 'material-ui/Divider';
import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText

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

const drawerWidth = 260;

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
  onLogout: (event) => void
};

export interface AppSideNavState {
}
class AppSideNav extends React.Component<AppSideNavProps,AppSideNavState> {
  constructor(props) {
    super(props);
    this.openPage = this.openPage.bind(this)
  }

  openPage(url) {
    History.push(url);
    window.scrollTo(0, 0)
    this.props.onRequestClose(null);
  }

  render() {
    return (
      <Drawer
      open={this.props.open}
      onRequestClose={this.props.onRequestClose}
      type={this.props.permanent?"permanent":"temporary"}

      anchor={"left"}>

      <div style={{width:drawerWidth}}>
      <div>
      <List>
        <ListItem button
                  onClick={()=>{this.openPage("/main/queue")}}>
          <ListItemIcon>
            <ListIcon />
          </ListItemIcon>
          <ListItemText primary="Now Playing" />
        </ListItem>
        <ListItem button
                  onClick={()=>{this.openPage("/main/library")}}>
          <ListItemIcon>
            <LibraryMusic />
          </ListItemIcon>
          <ListItemText primary="Library" />
        </ListItem>
        <ListItem button
                  onClick={()=>{this.openPage("/main/settings")}}>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Settings" />
        </ListItem>
      <Divider />
        <ListItem button
                  onClick={this.props.onLogout}>
          <ListItemIcon>
            <ExitToApp />
          </ListItemIcon>
          <ListItemText primary="Logout" />
        </ListItem>
      </List>
      <Divider />
      <List>
        <ListItem button>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Dummy 1" />
        </ListItem>
        <ListItem button>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Dummy 2" />
        </ListItem>
        <ListItem button>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Dummy 3" />
        </ListItem>
      </List>
  </div>
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
  screenHeight: number,
  headerHeight: number,
  pinNavBar: boolean
  showNavBar: boolean
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
                  screenHeight: 0,
                  headerHeight: 0,
                  pinNavBar: true,
                  showNavBar: false};
    this.logout = this.logout.bind(this)
    this.onResize = this.onResize.bind(this)
    this.openNavBar = this.openNavBar.bind(this)

  }

  logout(e) {
      e.preventDefault();
      this.props.logoutAndRedirect();
      this.setState({
          open: false,
      });
  }

  componentDidMount() {
    this.onResize()
    window.addEventListener('resize', this.onResize)

    const height = document.getElementById('AppHeader').clientHeight;
    this.setState({headerHeight:height})
  }

  componentWillUnmount() {
    window.removeEventListener('resize', this.onResize)
  }

  onResize() {
    // https://material.io/guidelines/layout/responsive-ui.html#responsive-ui-breakpoints

    this.setState({screenWidth:window.innerWidth,
                   screenHeight: window.innerHeight,
                   pinNavBar: window.innerWidth > 960})
  }

  openNavBar(open) {
    this.setState({showNavBar: open})
  }

  render() {

    let headerHeight = this.state.headerHeight;
    let _drawerWidth = this.state.pinNavBar?drawerWidth:0
    let navBar = <AppSideNav open={this.state.showNavBar}
                  permanent={this.state.pinNavBar}
                  onRequestClose={(e) => {this.openNavBar(false)}}
                  onLogout={(e)=>{this.logout(e)}}
                  />

    return (
      <div>

      <div id="AppHeader" style={{ position: "fixed",
                    height:{headerHeight},
                    width: "calc(100% - " +_drawerWidth+ "px)",
                    marginLeft: _drawerWidth,
                    background:"#455A64",
                    zIndex: 1000}} >
            <SoundView showMenuIcon={!this.state.pinNavBar}
                       openMenu={()=>{this.openNavBar(true)}}
                       />
      </div>

      {navBar}

      <main style={{ paddingTop: headerHeight, marginLeft: _drawerWidth }}>

      <h2>({this.state.headerHeight}) :: {this.state.screenWidth} x {this.state.screenHeight}
      {this.state.pinNavBar?"true":"false"}</h2>

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
